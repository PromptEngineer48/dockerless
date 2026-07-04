# Production pack — Dockerless paper video

Final cut: `output/dockerless_video.mp4` · 3:14 · 1080p30 · cloned voice via Qwen3-TTS

---

## Title options (pick one)

1. **Train Coding Agents WITHOUT Docker?! This New Paper Changes Everything**
2. **Docker is the Bottleneck — Dockerless Fixes AI Coding Agent Training**
3. **This AI Verifier Beats GPT-5.4 Without Running a Single Test**
4. **Dockerless: Environment-Free Training for Coding Agents (Paper Breakdown)**
5. **No Docker. No Tests. 62% on SWE-bench. How?!**

> Recommendation: #1 or #5 for CTR; #4 as the "searchable" safe pick.

---

## Description (copy-paste)

```
Training coding agents normally means building a Docker image for EVERY
repository — pinned dependencies, curated test suites, runners, parsers.
This new paper from Shanghai Jiao Tong University and the Douyin Group
throws all of that away.

Dockerless is an environment-free patch verifier: instead of executing
tests, it explores the repository like a senior code reviewer — spawning
parallel sub-agents that gather evidence with grep/find, then judging the
patch with a trained 9B model. The results are wild:

✅ 81.0 AUC as a verifier — beating GPT-5.4, GLM-5 and every open-source
   verifier (+14.3 points)
✅ Powers a FULLY environment-free post-training pipeline (SFT filtering
   + RL rewards)
✅ 62.0% on SWE-bench Verified, 50.0% Multilingual, 35.2% Pro — matching
   Docker-based training with zero Docker images

📄 Paper: https://arxiv.org/abs/2606.28436

⏱️ Chapters
0:00 Intro
0:16 The bottleneck: verification
0:44 The idea: judge, don't execute
1:05 How Dockerless works
1:37 Training the verifier
2:00 Verifier results (81 AUC)
2:21 Env-free post-training results
2:46 Why this matters
3:05 Outro

🎙️ Fun fact: the narration in this video is my voice cloned with the
open-source Qwen3-TTS from just a few seconds of reference audio.

#AI #CodingAgents #SWEbench #LLM #Docker #MachineLearning
```

---

## Tags

```
dockerless, coding agents, swe-bench, ai coding, llm training, reinforcement
learning, rlhf, program verifier, docker, environment-free, qwen, ai paper,
paper explained, software engineering ai, ai agents, code review ai, grpo,
rejection sampling, open source ai, voice cloning, qwen3-tts
```

---

## Thumbnail ideas

Rendered options are in `output/thumbs/` (run `python thumbnails.py`).
All leave the **left third free for your face cutout** — shocked/pointing
pose works best with these.

1. **"DOCKER IS DEAD?"** — giant crossed-out whale/container, red ✕,
   "for AI training" small tag. High shock value, matches title #1/#2.
2. **"BEATS GPT-5.4"** — huge "81.0 AUC" number with a mini bar chart
   showing Dockerless towering over GPT-5.4. Data-flex angle, title #3.
3. **"NO DOCKER · NO TESTS · 62%"** — three stacked punch lines with a
   green checkmark rail. Curiosity-gap angle, title #5.

Thumbnail rules of thumb used: ≤ 5 words of BIG text, one focal object,
dark bg + one accent color (blue #3987e5), readable at 168×94 px.

---

## Pinned comment idea

> Would you trust an AI verifier that never runs the tests? 🤔
> Also — this entire narration is a CLONED voice (open-source Qwen3-TTS,
> few seconds of reference audio). Drop a comment if you want a full
> tutorial on cloning your own voice locally.

## Community post / Short idea

- 15s Short: the "how it works" pipeline scene + hook "This AI judges code
  without ever running it" → drive to full video.
- Poll: "Would you train your coding agent env-free?" Yes / Only with tests /
  Hybrid
