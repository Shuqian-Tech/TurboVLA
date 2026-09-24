# FPGA / RTL Long-Horizon Exploration Agent --- Proposed Stack

> Goal: build a **non-linear, asynchronous, branchable FPGA design
> exploration framework**.\
> The AI/Codex layer proposes and modifies designs; infrastructure
> handles execution, parallel evaluation, state, retries, artifacts, and
> reproducibility.

## 1. Recommended stack at a glance

  --------------------------------------------------------------------------
  Layer                   Recommended choice      Role
  ----------------------- ----------------------- --------------------------
  Agent / reasoning       **Codex / LLM**         Analyze evidence, propose
                                                  RTL changes, debug, choose
                                                  next exploration action

  Main language           **Python 3.12+**        Glue code, scheduler
                                                  policy, evaluators, APIs

  RTL                     **SystemVerilog**       Primary hardware design
                                                  language

  Distributed execution   **Ray Core**            Async tasks, actors,
                                                  heterogeneous workers,
                                                  multi-machine execution

  Cluster deployment      **Kubernetes +          Containerized Ray
                          KubeRay**               clusters, heterogeneous
                                                  machines, scaling

  Durable workflow        **Do not add            Crash recovery / durable
                          initially**; later      long-running workflows if
                          evaluate **Temporal**   Ray + DB is insufficient

  State / metadata DB     **PostgreSQL**          Design graph, task state,
                                                  lineage, events, metrics
                                                  pointers

  Event / cache layer     **Redis** *(optional    Fast event/cache/pub-sub
                          initially)*             needs; don't make it
                                                  source of truth

  Artifact storage        **S3-compatible object  DCPs, bitstreams, logs,
                          store / MinIO**         reports, waveforms,
                                                  generated RTL

  Experiment UI/tracking  **MLflow** *(optional   Compare runs, metrics,
                          but useful)*            parameters and artifacts

  Container               **Docker**              Reproducible evaluator
                                                  environments

  RTL lint                **Verilator**           Fast compile/lint/static
                                                  checks

  Simulation              **XSim initially**      Functional simulation in
                                                  the existing Vivado flow

  FPGA synthesis/P&R      **Vivado**              synth → opt → place →
                                                  route →
                                                  timing/power/utilization

  Formal                  **SymbiYosys / Yosys**  Independent
                          *(where applicable)*    formal/property checks

  CI                      **GitHub Actions**      Framework/unit tests; not
                                                  the main FPGA execution
                                                  engine

  Observability           **OpenTelemetry +       Trace long distributed
                          Prometheus/Grafana**    exploration runs
                          *(later)*
  --------------------------------------------------------------------------

------------------------------------------------------------------------

## 2. The architecture I would use

``` text
                         ┌─────────────────────────┐
                         │      Codex / LLM        │
                         │  exploration policy     │
                         └───────────┬─────────────┘
                                     │
                              propose action
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────┐
│                    Exploration Controller                  │
│                                                            │
│   Design Graph + Policy + Event Handling + Budget Rules    │
│                                                            │
│   CONTINUE | FORK | RETRY | ROLLBACK | STOP | PROMOTE      │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
        PostgreSQL                     Artifact Store
   design/task/event state          RTL/DCP/log/waveform
               │
               ▼
┌────────────────────────────────────────────────────────────┐
│                        Ray Core                            │
│                distributed execution layer                │
└───────┬────────────┬──────────────┬─────────────┬──────────┘
        │            │              │             │
        ▼            ▼              ▼             ▼
   Verilator       XSim        Vivado Synth    Vivado P&R
   lint/check      simulation      / Impl       timing/QoR
        │            │              │             │
        └────────────┴────── events/results ──────┘
                              │
                              ▼
                       Controller reacts
                              │
                         new design(s)
```

The important point is that **this is not a DAG-only pipeline**.

The design history is a graph/tree of immutable design versions. An
evaluator finishing does not mean "go to the next stage"; it emits
evidence. The controller decides what that evidence means.

------------------------------------------------------------------------

## 3. Core data model

### `DesignState`

Every meaningful RTL revision becomes an immutable design node.

``` python
DesignState:
    design_id
    parent_design_id
    git_commit
    rtl_artifact
    constraints
    target_fpga

    hypothesis
    change_description
    created_by
    created_at
```

Do **not** overwrite an old design.

A modification creates:

``` text
D17
├── D18  timing optimization
├── D19  pipeline experiment
└── D20  memory architecture experiment
```

This is what makes rollback and branching natural.

### `Evaluation`

``` python
Evaluation:
    evaluation_id
    design_id

    evaluator_type
    status

    metrics
    artifact_refs
    log_ref

    started_at
    finished_at
```

Example evaluator types:

``` text
lint
compile
unit_sim
full_sim
formal
synthesis
place
route
timing
power
resource
benchmark
```

### `Event`

Everything important becomes an event:

``` text
DESIGN_CREATED
LINT_FAILED
SIM_PASSED
SIM_FAILED
SYNTH_FINISHED
ROUTE_FAILED
TIMING_FINISHED
QOR_IMPROVED
QOR_REGRESSED
WORKER_FAILED
BUDGET_EXCEEDED
```

The agent/controller reacts to events rather than waiting for a rigid
pipeline.

------------------------------------------------------------------------

## 4. Evaluators should be independent

Define one common interface:

``` python
class Evaluator:
    def can_run(design): ...
    def resources(design): ...
    def run(design): ...
    def parse_result(output): ...
```

Implementations:

``` text
VerilatorEvaluator
XSimEvaluator
VivadoSynthEvaluator
VivadoImplementationEvaluator
TimingEvaluator
ResourceEvaluator
FormalEvaluator
BenchmarkEvaluator
```

Then adding another tool does not require redesigning the orchestration
system.

For example, later:

``` text
JacquardEvaluator
IcarusEvaluator
QuestaEvaluator
VCS/Evaluator
YosysEvaluator
HLSCompilerEvaluator
```

------------------------------------------------------------------------

## 5. Why Ray Core belongs here

Use Ray primarily as the **execution substrate**, not as the
intelligence of the system.

Ray handles:

``` text
task submission
async execution
parallel workers
CPU/GPU/custom-resource scheduling
stateful workers via Actors
multi-node execution
failure/retry primitives
```

Define custom capabilities such as:

``` text
vivado = 1
xsim = 1
gpu = 1
formal = 1
board_kr260 = 1
board_arty_a7 = 1
```

A task asks for a capability rather than a hostname.

Conceptually:

``` python
@ray.remote(resources={"vivado": 1})
def run_vivado(design):
    ...
```

That means the exploration controller does **not** need to know whether
Vivado is running on:

``` text
local workstation
lab server
remote bare-metal machine
Kubernetes worker
cloud VM
```

------------------------------------------------------------------------

## 6. Kubernetes layer

Use:

``` text
Kubernetes
   └── KubeRay
         ├── Ray head
         ├── generic CPU workers
         ├── GPU workers
         ├── Vivado workers
         └── simulation workers
```

I would **not** make Kubernetes itself understand FPGA exploration
logic.

Kubernetes manages machines/containers.

Ray manages distributed computation.

Your controller manages **design exploration**.

Keep those responsibilities separate.

------------------------------------------------------------------------

## 7. Agent layer

Codex should **not** be responsible for:

``` text
keeping queues alive
remembering which process is running
retrying infrastructure failures
tracking artifacts
maintaining distributed locks
knowing physical worker addresses
```

Give Codex a structured state such as:

``` text
DESIGN D31

Goal:
maximize Fmax × IPC

Parent:
D27

Changes:
- split multiplier pipeline
- changed FIFO depth

Available evidence:
lint       PASS
unit_sim   PASS
full_sim   RUNNING
synthesis  PASS
route      RUNNING
timing     pending

Current metrics:
LUT       41,203
FF        38,221
BRAM      74
DSP       128

Parent metrics:
LUT       39,850
Fmax      187 MHz
IPC       1.34

Budget:
3 parallel experiments available
```

Then ask it for an **action**, not arbitrary orchestration.

Example:

``` json
{
  "action": "fork",
  "parent": "D31",
  "hypothesis": "FIFO depth increase caused LUT regression",
  "changes": ["restore FIFO depth while retaining multiplier pipeline"],
  "evaluations": ["lint", "unit_sim", "synthesis"]
}
```

The controller validates and executes that decision.

------------------------------------------------------------------------

## 8. Exploration policy

Start deterministic.

Do **not** begin by asking the LLM to control everything.

### V0

``` text
if lint fails:
    ask agent to repair

if unit simulation fails:
    ask agent to debug

if functional checks pass:
    launch synthesis

if synthesis succeeds:
    launch implementation

if QoR improves:
    preserve candidate

if QoR regresses:
    preserve result but lower priority

if hypothesis remains interesting:
    fork another design
```

### V1

Allow several candidate designs simultaneously.

``` text
                  D0
            ┌─────┼─────┐
            D1    D2    D3
           /  \          |
         D4    D5        D6
```

The controller allocates compute budget among them.

### V2

Agent chooses:

``` text
which branch to expand
which evaluator to run
whether more evidence is worth its cost
whether to abandon a branch
whether to revisit an older design
```

### V3

Add learned search policy / evolutionary search / bandits if useful.

The infrastructure does not need to change.

------------------------------------------------------------------------

## 9. Cheap checks before expensive checks

Although evaluations are asynchronous, cost still matters.

Suggested cost hierarchy:

``` text
                    COST

Verilator lint       $
unit simulation      $
formal subset       $$
synthesis           $$$
full simulation     $$$
place & route      $$$$
hardware benchmark $$$$$
```

The scheduler should be allowed to launch independent checks
concurrently, but it should avoid wasting expensive FPGA compilation on
obviously broken candidates.

So the model is:

**asynchronous dependency graph**, not "everything always runs
immediately."

------------------------------------------------------------------------

## 10. Artifact strategy

Never pass giant FPGA artifacts through the scheduler itself.

Store large outputs in object storage:

``` text
artifacts/
  project/
    design_id/
      source/
      logs/
      simulation/
      synthesis/
      implementation/
      timing/
      checkpoints/
```

Typical artifacts:

``` text
SystemVerilog source
testbench
XDC
Vivado Tcl
XSim waveform
synthesis report
utilization report
timing report
power report
post-synth DCP
post-route DCP
bitstream
agent patch
agent reasoning summary
```

Ray/Postgres should mostly pass **references/metadata**, not multi-GB
artifacts.

------------------------------------------------------------------------

## 11. Reproducibility

Each design should resolve to:

``` text
git commit
+
container image digest
+
FPGA target
+
tool version
+
constraints
+
Tcl/config
+
parent design
+
agent action
```

That lets you reproduce an experiment months later.

For Vivado specifically, tool version should be first-class metadata
because results can change across versions.

------------------------------------------------------------------------

## 12. Temporal: add only if needed

I would **not** start with both Ray and Temporal.

First build:

``` text
Python
PostgreSQL
Ray
Vivado/XSim/Verilator
artifact store
Codex
```

If later you need workflows that must survive controller crashes,
upgrades, multi-day waits and complicated durable retries, evaluate
**Temporal**.

A possible mature architecture is:

``` text
Temporal
   │
   └── durable exploration workflow
          │
          ▼
        Ray
          │
          └── distributed compute
```

But that is unnecessary complexity for V0.

------------------------------------------------------------------------

## 13. MLflow: useful but not the source of truth

MLflow is useful for viewing:

``` text
Design       Fmax      IPC      LUT      FF       Power
D17          181       1.31     39k      36k      ...
D18          196       1.30     42k      38k      ...
D19          190       1.37     40k      37k      ...
```

and associating artifacts/parameters with runs.

But your **Design Graph belongs in PostgreSQL**.

MLflow should be a visualization/experiment-tracking layer, not the
orchestration database.

------------------------------------------------------------------------

## 14. Suggested repository layout

``` text
fpga-explorer/
│
├── controller/
│   ├── scheduler.py
│   ├── policy.py
│   ├── events.py
│   ├── design_graph.py
│   └── budgets.py
│
├── agent/
│   ├── codex.py
│   ├── context_builder.py
│   ├── actions.py
│   └── prompts/
│
├── evaluators/
│   ├── base.py
│   ├── verilator.py
│   ├── xsim.py
│   ├── vivado_synth.py
│   ├── vivado_impl.py
│   ├── timing.py
│   └── formal.py
│
├── execution/
│   ├── ray_tasks.py
│   ├── resources.py
│   └── workers.py
│
├── state/
│   ├── models.py
│   ├── repository.py
│   └── migrations/
│
├── artifacts/
│   └── store.py
│
├── rtl/
│
├── testbenches/
│
├── containers/
│
├── deploy/
│   ├── docker/
│   └── kuberay/
│
└── tests/
```

------------------------------------------------------------------------

## 15. Minimal starting stack

For the first prototype, deliberately keep it small:

``` text
Python
SystemVerilog
Codex
Ray Core
SQLite/PostgreSQL
local filesystem
Verilator
XSim
Vivado
Git
```

One workstation is enough.

Prove this loop:

``` text
            ┌──────────────┐
            │ Design D0    │
            └──────┬───────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
       lint       XSim      synthesis
        │          │          │
        └────── events ───────┘
                   │
                   ▼
              Controller
                   │
                   ▼
                 Codex
                   │
             ┌─────┴─────┐
             ▼           ▼
            D1           D2
```

Only after this works add:

``` text
PostgreSQL
MinIO/S3
Docker
Kubernetes
KubeRay
MLflow
multiple physical machines
```

------------------------------------------------------------------------

## 16. What I would *not* use initially

Avoid making these foundational:

``` text
Airflow
traditional finite-state-machine framework
Celery as the core exploration model
LangGraph as infrastructure scheduler
Kubernetes Jobs directly controlled by the LLM
a giant custom queue implementation
```

They can solve pieces of the problem, but they should not define the
architecture.

The distinctive abstraction of this project should be:

> **Versioned Design Graph + asynchronous Evaluators + event-driven
> Exploration Policy**

not:

> "an LLM wrapped around a Vivado pipeline."

------------------------------------------------------------------------

## 17. V0 implementation milestone

The first milestone should demonstrate exactly one thing:

**A single parent RTL design automatically produces multiple candidate
children, evaluates them asynchronously, accumulates late-arriving
evidence, and chooses what to explore next without requiring a linear
pipeline.**

Example:

``` text
D0
│
├── D1 ─ lint ✓ ─ sim ✓ ─ synth ✓ ─ route ........ ✓
│
├── D2 ─ lint ✓ ─ sim ✗
│
└── D3 ─ lint ✓ ─ sim ✓ ─ synth ........ ✓
                                   │
                                   └── agent creates D4
                                        before D1 route
                                        has even finished
```

If this works cleanly, the core architecture is validated.

------------------------------------------------------------------------

## 18. Recommended implementation order

1.  **DesignState + Evaluation + Event schemas**
2.  **Local evaluator interface**
3.  **Verilator + XSim evaluators**
4.  **Vivado synthesis evaluator**
5.  **Ray task execution**
6.  **Event-driven controller**
7.  **Codex action schema**
8.  **Design branching / rollback**
9.  **Vivado implementation + QoR extraction**
10. **PostgreSQL persistence**
11. **Artifact store**
12. **Docker**
13. **Multi-machine Ray**
14. **KubeRay / Kubernetes**
15. **MLflow dashboard**
16. Only then consider **Temporal / learned scheduling / evolutionary
    policies**

------------------------------------------------------------------------

## Core design principle

**Ray schedules compute.**

**Kubernetes schedules infrastructure.**

**PostgreSQL remembers truth.**

**Object storage remembers artifacts.**

**Evaluators produce evidence.**

**Codex proposes design decisions.**

**Your Exploration Controller decides how FPGA design search evolves.**
