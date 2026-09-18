# AI Development Transcripts

This directory contains the complete, unedited development transcripts and session logs for the BhuMe Land-Boundary Correction project, as required by the submission guidelines (*"If the repo doesn't have raw chat transcripts, your application won't be considered"*).

## Files in this Directory

1. **[`antigravity-bhume.md`](antigravity-bhume.md)**:
   - **Primary Antigravity Coding Transcript**: Contains the complete, chronological record of all user prompts, engineering constraints, intermediate development actions, and AI assistant responses during implementation in Google DeepMind Antigravity.
   - **Verbatim & Unedited**: Preserves all 6 conversation turns, reasoning steps, code decisions, evaluation outputs, and iterative refinements.

2. **[`antigravity-bhume.jsonl`](antigravity-bhume.jsonl)**:
   - **Exact Native Session Log**: The raw JSONL conversation trajectory exported directly from the Google DeepMind Antigravity environment (`Conversation ID: 610f33dd-5025-40df-b0a3-321c4a23ea0f`).
   - Contains all machine-readable step metadata, timestamps, tool calls, and execution outputs.

3. **[`chatgpt-bhume.md`](chatgpt-bhume.md)**:
   - **Problem Understanding & Strategy Transcript**: Contains the visible User ↔ Assistant transcript from ChatGPT covering the initial exploration of the BhuMe problem, contract/rubric analysis, strategy formulation, walkthrough reviews, and video preparation.

## Overview of Development Progression

The session logs document the complete step-by-step engineering journey:
- **Phase 1 (ChatGPT)**: Problem understanding, contract and scoring rubric breakdown, strategy design (prioritizing restraint, local translation, satellite edges over boundary hints, avoiding ML overengineering).
- **Phase 2 (Antigravity)**: Downloading official datasets, building metric reprojection (`EPSG:4326` $\leftrightarrow$ `EPSG:3857`), implementing Sobel edge filtering and patch extraction, writing the translation grid-search algorithm.
- **Phase 3 (Validation & Refinement)**: Running evaluation on ground truths, resolving the Malatavadi Plot 1177 false correction via boundary agreement corroboration, enforcing strict radius bounding ($25.0\,\text{m}$) on Plot 2647, calibrating confidence, and generating full predictions for both villages.
