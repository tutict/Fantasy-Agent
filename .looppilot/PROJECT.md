# EXP-007 Project

Objective: run one third-project behavioral replication of LoopPilot Phase 9 in
Fantasy-Agent and make at most one evidence-backed bounded product change.

Mode: Lightweight + Security Review.

Product agents such as ComfyUI Worker and Creative Review Agent are domain actors;
they do not hold LoopPilot Supervisor, Worker, Reviewer, or Integrator authority.
No delegated LoopPilot Worker is used.

Authority: the user authorized an experiment branch, commits, and push of that branch
only. Main, merge, PR, release, deploy, real external-tool execution, and LoopPilot
modification are outside scope.
