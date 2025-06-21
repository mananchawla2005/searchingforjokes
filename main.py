import requests
import os
from dotenv import load_dotenv
from itertools import combinations
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import shelve
from limit import *
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
load_dotenv() 

invalidate_cache = False
ideas = ['superman']
topic = ideas[0]
n1 = 5
n2 = 5

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

def generate_combinations(lst):
    result = []
    for r in [1, 2]:
        result.extend(combinations(lst, r))
    return result

# @rate_limiter(max_calls=100, period=60)
def send_request(msg, max_tokens=1024):
    # url = "https://api.hyperbolic.xyz/v1/chat/completions"
    url = os.environ['BASE_URL']
    headers = {
        "Content-Type": "application/json",
        # "Authorization": f"Bearer {os.environ['API_KEY']}"
    }
    if(os.environ['API_KEY']):
        headers['Authorization'] = f"Bearer {os.environ['API_KEY']}"
    data = {
        "messages": msg,
        # "model": "deepseek-ai/DeepSeek-V3-0324",
        "model": "RedHatAI/gemma-3-27b-it-FP8-dynamic",
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "top_p": 0.9
    }

    if(os.environ['MODEL']):
        data['model'] = os.environ['MODEL']

    response = session.post(url, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

# First Order Prompts

SYSTEM_PROMPT_JOKE_OBS1 = {
    "role": "system",
    "content": (
        "You are an expert stand-up comedian and joke writer. "
        "You will be given a topic for a joke. "
        "You will return several useful, non-obvious, and creative observations or angles "
        "about this topic that could serve as building blocks for a joke. "
        "You will NOT return any jokes themselves. "
        "Be as creative and surprising as possible."
    )
}
USER_PROMPT_JOKE_OBS1 = {
    "role": "user",
    "content": (
        "Here is the topic for a joke:\n\n"
        "{topic}\n\n"
        "Brainstorm a list of {num_observations} non-obvious, creative observations or angles "
        "about this topic. Each observation should be a short phrase or sentence—no punchlines yet. Give it in numbered bullets format."
    )
}
USER_PROMPT_JOKE_OBS1["content"] = USER_PROMPT_JOKE_OBS1["content"].format(
    topic=topic,
    num_observations=n1
)

# foo = first order observations
with shelve.open('cache.tmp', writeback=True) as f:
  foo = f.get('foo', None)
  if not (foo) or invalidate_cache:
    foo = list(filter(lambda x: x.strip()!="", send_request([SYSTEM_PROMPT_JOKE_OBS1,USER_PROMPT_JOKE_OBS1]).split('\n')))
    foo = generate_combinations(foo)
    f['foo'] = foo

# Second Order Prompts

SYSTEM_PROMPT_JOKE_OBS2 = {
    "role": "system",
    "content": (
        "You are an expert stand-up comedian and joke writer. "
        "You will be given a topic and several initial observations about it. "
        "You will brainstorm several new, useful, and creative observations or angles about the topic, "
        "derived from those given. "
        "You will NOT return any jokes. Be as inventive as possible."
    )
}

USER_PROMPT_JOKE_OBS2 = {
    "role": "user",
    "content": (
        "Here is the topic:\n\n"
        "{topic}\n\n"
        "Here are some initial observations:\n"
        "{observations}\n\n"
        "Generate {num_new_obs} fresh, non-obvious observations or angles inspired by the above. Give it in numbered bullets format."
    )
}


# soo = second order observations
with shelve.open('cache.tmp', writeback=True) as f:
    soo = f.get('soo', None)
    if not (soo) or invalidate_cache:
        soo = [None] * len(foo)  
        
        prompts = []
        indices = []
        for i in range(len(foo)):
            obs = '\n'.join(foo[i])
            prompt_content = USER_PROMPT_JOKE_OBS2["content"].format(
                topic=topic,
                num_new_obs=n2,
                observations=obs
            )
            prompts.append([SYSTEM_PROMPT_JOKE_OBS2, {"role": "user", "content": prompt_content}])
            indices.append(i)
        
        with ThreadPoolExecutor(max_workers=500) as executor:
            future_to_index = {executor.submit(send_request, prompt): idx for prompt, idx in zip(prompts, indices)}
            
            for future in tqdm(as_completed(future_to_index), total=len(future_to_index), desc="Second order observations"):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    temp_obs = list(filter(lambda x: x.strip()!="", result.split('\n')))
                    soo[idx] = generate_combinations(temp_obs)
                except Exception as e:
                    print(f"Error in second order observation {idx}: {e}")
                    soo[idx] = [] 
        
        f['soo'] = soo
  

# Outline Prompts

SYSTEM_PROMPT_JOKE_OUTLINE = {
    "role": "system",
    "content": (
        "You are an expert stand-up comedian and joke writer. "
        "You will be given a topic and a carefully chosen set of observations. "
        "You will use them to brainstorm a natural-language outline for a joke. "
        "Quote each observation exactly before you use it as you build your outline. "
        "Do NOT write the full joke yet—just the structure and key beats."
    )
}

USER_PROMPT_JOKE_OUTLINE = {
    "role": "user",
    "content": (
        "Topic:\n\n"
        "{topic}\n\n"
        "Observations to use:\n"
        "{observations}\n\n"
        "Create a step-by-step outline of a joke that weaves in these observations. "
        "Quote each one exactly before the step that uses it."
    )
}

with shelve.open('cache.tmp', writeback=True) as f:
  outlines = f.get('outlines', None)
  if not (outlines) or invalidate_cache:
    observations = []
    for first, second in zip(foo, soo):
      for second_set in second:
        obs = ""
        obs += "\n".join(first)+"\n"
        obs += "\n".join(second_set)
        observations.append(obs)
    with ThreadPoolExecutor(max_workers=500) as executor:
        # submit tasks
        future_to_obs = {
            executor.submit(send_request,
                            [SYSTEM_PROMPT_JOKE_OUTLINE, {"role": USER_PROMPT_JOKE_OUTLINE["role"], "content": USER_PROMPT_JOKE_OUTLINE["content"].format(
                              topic=topic,
                              observations=obs
                            )}],
                            max_tokens=4096
                          ): o
            for o in observations
        }

        outlines = []
        for future in tqdm(as_completed(future_to_obs), total=len(future_to_obs), desc="joke outlines"):
            obs = future_to_obs[future]
            try:
                outline = future.result()
            except Exception as e:
                continue
            outlines.append({"observations": obs, "outline": outline})
    f['outlines'] = outlines

# Self Critique and variation prompts


SYSTEM_PROMPT_JOKE_VARIATION = {
    "role": "system",
    "content": (
        "You are an expert stand-up comedian and joke editor. "
        "You will be given a draft joke outline. "
        "First, point out its weaknesses or places it could be funnier. "
        "Then, using those criticisms, generate an alternative outline that fixes them. "
        "Do NOT write any full jokes—only outlines."
    )
}

USER_PROMPT_JOKE_VARIATION = {
    "role": "user",
    "content": (
        "Draft outline:\n\n"
        "{joke_outline}\n\n"
        "Identify specific weaknesses or missed opportunities. "
        "Then produce a revised joke outline that addresses each issue."
    )
}

with shelve.open('cache.tmp', writeback=True) as f:
  alt_outlines = f.get('alt_outlines', None)
  if not (alt_outlines) or invalidate_cache:
  # if True:
    alt_outlines = []
    with ThreadPoolExecutor(max_workers=500) as executor:
        # submit tasks
        future_to_obs = {
            executor.submit(send_request,
                            [SYSTEM_PROMPT_JOKE_OUTLINE, {"role": USER_PROMPT_JOKE_VARIATION["role"], "content": USER_PROMPT_JOKE_VARIATION["content"].format(joke_outline=o['outline'])}],
                            max_tokens=4096
                          ): o['observations']
            for o in f.get('outlines', [])
        }

        alt_outlines = []
        for future in tqdm(as_completed(future_to_obs), total=len(future_to_obs), desc="joke variants"):
            obs = future_to_obs[future]
            try:
                alt_outline = future.result()
            except Exception as e:
                continue
            alt_outlines.append({"observations": obs, "outline": alt_outline})
    f['alt_outlines'] = alt_outlines


# Joke creation prompt pass@225 

SYSTEM_PROMPT_JOKE_FINAL = {
    "role": "system",
    "content": (
        "You are an expert stand-up comedian and joke writer. "
        "You will be given a topic, all selected observations, and two competing outline drafts. "
        "Now write the final joke in natural language, blending the best elements of both outlines. "
        "Make it cohesive, punchy, and quote any observation when it directly informs a line."
    )
}

USER_PROMPT_JOKE_FINAL = {
    "role": "user",
    "content": (
        "Topic:\n\n"
        "{topic}\n\n"
        "Observations:\n"
        "{obs}\n\n"
        "Outline A:\n\n"
        "{joke_outline}\n\n"
        "Outline B:\n\n"
        "{alt_joke_outline}\n\n"
        "Write the final joke, weaving in the above. "
        "Quote any observation exactly when you use it."
    )
}


with shelve.open('cache.tmp', writeback=True) as f:
  jokes = f.get('jokes', None)
  if not (jokes) or invalidate_cache:
  # if True:
    jokes = []
    with ThreadPoolExecutor(max_workers=500) as executor:
        # submit tasks
        future_to_obs = {
            executor.submit(send_request,
                            [SYSTEM_PROMPT_JOKE_FINAL, {"role": USER_PROMPT_JOKE_FINAL["role"], "content": USER_PROMPT_JOKE_FINAL["content"].format(
                               joke_outline=o['outline'],
                               alt_joke_outline=a['outline'],
                               obs=o['observations'],
                               topic=topic
                            )}],
                            max_tokens=4096
                          ): o['observations']
            for o,a in zip(f.get('outlines', []), f.get('alt_outlines',[]))
        }

        jokes = []
        for future in tqdm(as_completed(future_to_obs), total=len(future_to_obs), desc="jokes"):
            obs = future_to_obs[future]
            try:
                joke = future.result()
            except Exception as e:
                continue
            jokes.append(joke)
    f['jokes'] = jokes


with open('COMEDY.md', 'r', encoding='utf-8') as f:
  comedy_notes = f.read()

SYSTEM_PROMPT_VERIFY = {
    "role": "system",
    "content": """You are an expert comedy critic and joke analyst. You will evaluate jokes based on:
1. Brevity (1-10): How concise and punchy is the joke?
2. Coherence (1-10): How well do the parts connect?
3. Originality (1-10): How unique/surprising is the perspective?
4. Punchline Impact (1-10): How strong is the payoff?
5. Audience Appeal (1-10): How relatable/accessible is it?

Return your analysis as a JSON object with these scores and a brief explanation.
Focus on evaluating standalone, short-form jokes rather than long bits.
"""
}

USER_PROMPT_VERIFY = {
    "role": "user", 
    "content": """Here is a comedy writing guide excerpt for reference:
{comedy_guide}

Please evaluate this joke:
{joke}

Provide scores and brief explanation in this JSON format:
{{
    "brevity": score,
    "coherence": score, 
    "originality": score,
    "punchline": score,
    "appeal": score,
    "explanation": "brief_explanation"
}}"""
}

def clean_json_string(s):
    """Clean and validate JSON string before parsing"""
    # Find the first { and last }
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1:
        raise ValueError("No valid JSON object found")
    
    # Extract just the JSON object
    json_str = s[start:end+1]
    return json_str

def validate_score(score):
    """Validate score object has required fields and valid values"""
    required_fields = ['brevity', 'coherence', 'originality', 'punchline', 'appeal', 'explanation']
    
    # Check all fields exist
    if not all(field in score for field in required_fields):
        return False
        
    # Validate numeric scores are between 1-10
    numeric_fields = ['brevity', 'coherence', 'originality', 'punchline', 'appeal']
    for field in numeric_fields:
        try:
            value = float(score[field])
            if not (1 <= value <= 10):
                return False
        except (ValueError, TypeError):
            return False
            
    return True

# Replace the scoring section with:
with shelve.open('cache.tmp', writeback=True) as f:
    scores = f.get('scores', None)
    if not (scores) or invalidate_cache:
    # if True:
        scores = []
        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_obs = {
                executor.submit(send_request,
                    [SYSTEM_PROMPT_VERIFY, {"role": USER_PROMPT_VERIFY["role"], 
                     "content": USER_PROMPT_VERIFY["content"].format(
                        comedy_guide=comedy_notes,
                        joke=joke
                    )}],
                    max_tokens=4096
                ): joke
                for joke in jokes
            }

            scores = []
            for future in tqdm(as_completed(future_to_obs), 
                             total=len(future_to_obs), 
                             desc="joke scores"):
                joke = future_to_obs[future]
                try:
                    result = future.result()
                    json_str = clean_json_string(result)
                    score = json.loads(json_str)
                    
                    if not validate_score(score):
                        raise ValueError(f"Invalid score format: {score}")
                        
                    score['total'] = (score['brevity'] + score['coherence'] + 
                                    score['originality'] + score['punchline'] + 
                                    score['appeal'])
                    scores.append({
                        "joke": joke,
                        "score": score
                    })
                except Exception as e:
                    print(f"Error processing joke: {str(e)}")
                    if 'result' in locals():
                        print("Raw response was:\n", result)
                    continue
        f['scores'] = scores

# Sort by total score
top_jokes = sorted(scores, 
                  key=lambda x: x["score"]["total"], 
                  reverse=True)[3]

# print(f"Total jokes processed: {len(jokes)}")
# print(f"Total scores generated: {len(scores)}")
# for i, entry in enumerate(top_jokes, 1):
#     print(f"\n{i}. Score: {entry['score']['total']}/50")
#     print(f"Joke: {entry['joke'][:100]}...")  # Print first 100 chars of joke
# with open(f"{topic}.json", "w") as f:
#   json.dump(top_jokes, f, indent=4)

print(top_jokes)