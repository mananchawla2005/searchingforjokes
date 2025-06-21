
---

# Jokesearch: Plan-Based Joke Generation with LLMs

### An implementation of PlanSearch adapted for humor generation

Large Language Models (LLMs) have made significant progress in language understanding and generation, yet consistently struggle with humor—especially in generating genuinely funny jokes or stand-up bits. Most attempts feel templated, stale, or just unfunny. This project adapts the **PlanSearch** methodology to **joke generation**, creating a structured pipeline to first ideate and then refine humorous content with an LLM-as-a-judge mechanism.

---

## 💡 Motivation

LLMs today often fail to consistently generate jokes that land. Most outputs are either repetitive, overly safe, or lack the surprising misdirection that real humor needs. This project tackles that gap by applying a planning-based search method to widen the exploration space for humor, identify novel ideas, and use a verifier LLM to prune for creativity and quality. This work was inspired by the PLANSEARCH paper (ICLR 2024) and extended to a domain where evaluation is non-deterministic: comedy.

---

## 🧠 Key Ideas

* **Planning with LLMs**: Generate diverse *idea candidates* (premise-level humor), then expand each into full jokes using a second-stage generation.
* **LLM-as-a-Judge**: Use a language model not just to generate but also evaluate humor, guided by heuristics like creativity, misdirection, and relatability.
* **External Knowledge Boost**: Enhanced judge reasoning using a Deep Research report on writing comedy to act as contextual guidance for evaluation.
* **Novelty Evaluation**: Explored generation diversity by analyzing how significantly PlanSearch output diverges from base model completions (e.g., via KL divergence).
* **Instruction Tuning Hacks**: Techniques like dynamic temperature scaling and prompt randomization helped increase idea diversity in instruction-tuned models.

---

## 🧪 Results

### Example Topic: `penguin`

**Generated Joke:**

> *You ever think about how penguins are just birds that gave up on their one job? Like, technically birds, right? But they just…didn’t bother. “Penguins are essentially birds that evolved to be terrible at their one defining trait: flying.” It’s like getting mad at a fish for not being able to do taxes. It’s just…not their skillset. We’re the ones projecting!*
>
> *But they didn’t just give up. They doubled down on not flying. They became masters of waddling, experts in sliding on their bellies. It’s…impressive, in a deeply unsettling way. And then they built a whole society around it.*
>
> *Because “Penguins are the ultimate corporate team players – They thrive in harsh conditions by huddling together for warmth, essentially turning teamwork into a survival strategy. It’s like they’re the middle managers of the animal kingdom: always in formation, never breaking rank.”*
>
> *I’m telling you, penguin society is brutal. They have mandatory 'Huddle Time' every two hours. If you’re not sufficiently close to your colleagues, HR will issue a 'Chill Deficiency Warning'.*
>
> *And the performance reviews? All based on how well you maintain body temperature. It’s a nightmare.*
>
> *You know what the ultimate punishment is in penguin corporate? They make you lead the 'Flight Initiative'. It’s a completely pointless committee dedicated to brainstorming ways to fly. Years of wasted time, endless powerpoint presentations…it’s basically any tech company.*
>
> *(Pauses, looks thoughtful)*
> *Honestly, looking at penguins, I’m starting to think maybe giving up on your dreams isn’t so bad. I mean, at least they’re warm.*

---

## 🤯 Takeaways

* LLMs *can* be funny when given the right planning structure and evaluation signals.
* Surprisingly, jokes generated through PlanSearch were often original, layered, and showed misdirection—an essential humor ingredient.
* Contrary to common belief, the funniest completions weren’t always memorized. Many jokes included unusual analogies (like “penguin as middle manager”) that show true generalization.

---

## 📚 Implementation Details

* **Model**: [`gemma`](https://aclanthology.org/2025.cmcl-1.6.pdf) used for both generation and verification, as it's shown to perform well in humor contexts.
* **Evaluation Guidance**: Custom comedy-style prompt injection using excerpts from a deep writing guide on humor and misdirection.
* **Inference**: Follows the OpenAI-compatible API format.

---

## 🔧 Setup

Add the following to your `.env`:

```dotenv
BASE_URL=your_model_server_url
API_KEY=your_api_key_here
MODEL=model_name_here
```

```bash
python main.py
```
---

## 📎 References

* PlanSearch Paper (ICLR 2024)
* [FunnyGPT Article](https://freedium.cfd/https://medium.com/the-generator/how-i-built-funnygpt-an-ai-model-that-writes-standup-comedy-462e4485fd93)
