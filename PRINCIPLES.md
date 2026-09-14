# KATALYST — NON-NEGOTIABLE PRODUCT PRINCIPLES

Before doing ANY research, architecture proposal, or implementation, understand this:

The goal is NOT to make Katalyst have the most features.

The goal is to make Katalyst feel:

> FAST.  
> STABLE.  
> RESPONSIVE.  
> CALM.  
> NATIVE.  
> PREDICTABLE.  
> DELIGHTFUL.  

The quality bar should feel closer to a polished native application such as Codex / Zed than a feature-heavy web dashboard.

---

## 1. STABILITY > FEATURES
This is the highest-priority rule.  
A feature that makes Katalyst less stable is NOT worth shipping.  
A feature that increases:
* crashes
* freezes
* UI stalls
* race conditions
* memory leaks
* startup time
* background CPU
* unnecessary network activity
* state corruption
* session loss
* rendering instability

must be rejected, redesigned, or deferred.  
NEVER sacrifice application stability to add functionality.  
If forced to choose:  
`STABILITY > PERFORMANCE > UX POLISH > FEATURES`  
Actually, treat performance and UX polish as part of quality rather than optional features.

---

## 2. NATIVE APP FEEL
Katalyst should feel like a real native development tool.  
It should NOT feel like:
* Electron bloat
* a web dashboard wrapped in a desktop shell
* an admin panel
* a collection of AI widgets
* a collection of disconnected features

Prefer:
* native GPUI interactions
* native scrolling
* native keyboard behavior
* native focus management
* native menus
* native dialogs
* smooth transitions
* predictable state changes
* minimal visual noise

The user should forget that multiple subsystems exist underneath. Everything should feel like ONE application.

---

## 3. CODEX-LIKE CALMNESS
Study the feel of Codex carefully. The objective is NOT to copy its UI. Understand why it feels calm.  
Avoid:
* excessive badges
* excessive animations
* giant cards
* noisy dashboards
* unnecessary progress indicators
* constant status changes
* too many buttons
* duplicated information
* permanent AI chrome

Prefer:
* strong hierarchy
* compact information density
* clear state
* subtle progress
* meaningful status
* progressive disclosure

The UI should communicate: *"I know what is happening."* rather than: *"LOOK! AI IS DOING SOMETHING!"*

---

## 4. RESPONSIVENESS IS A FEATURE
Typing must remain instant.  
Scrolling must remain smooth.  
Opening files must feel immediate.  
Switching agents must feel immediate.  
Opening a diff must feel immediate.  
The UI must never wait for:
* model inference
* network requests
* MCP calls
* filesystem scans
* git operations
* repository indexing
* transcript parsing
* tool execution

All expensive work must happen asynchronously/backgrounded. NEVER block the UI thread.

---

## 5. OPTIMIZE FOR PERCEIVED PERFORMANCE
Do not only optimize benchmarks. Optimize what the user FEELS.  
Bad:  
`User clicks agent → spinner → wait → UI appears`  
Good:  
`User clicks agent → UI switches immediately → cached state appears → background data refreshes`  
Use:
* optimistic UI where safe
* incremental rendering
* progressive loading
* caching
* background indexing
* incremental parsing
* streaming

The interface should respond before expensive work finishes whenever safe.

---

## 6. AVOID "FEATURE BLOAT"
Every proposed feature must answer:
* WHY does the user need this?
* WHAT problem does it solve?
* HOW often will it be used?
* DOES it simplify the workflow?
* DOES it make Katalyst feel better?

If the feature exists only because "Cursor has it", "Orca has it", or "omp-deck has it", that is NOT sufficient justification. Katalyst should adopt PRINCIPLES, not feature checklists.

---

## 7. PROGRESSIVE DISCLOSURE
Do not expose everything at once.  
* **Primary UI**: Current task, current agent state, relevant changes, next action.  
* **Secondary UI**: Tools, context, MCP, skills, logs, metadata.  
* **Advanced UI**: Raw events, protocol information, debug information, token details, internal state.  
Hide complexity until the user asks for it.

---

## 8. NO REDUNDANT STATE
Avoid creating multiple sources of truth.  
* If OMP owns agent/session state: Katalyst should not create a second competing agent state system.  
* If Git owns repository state: Do not duplicate it unnecessarily.  
* If ACP owns protocol/session communication: Use ACP rather than inventing another transport.  
Prefer adapters and views over duplicate systems.

---

## 9. MINIMIZE BACKGROUND WORK
Do not continuously poll, scan the repository, parse everything, refresh UI, query MCP, recompute context, or recalculate metadata unless necessary.  
Prefer:
* events
* subscriptions
* incremental updates
* lazy loading
* cache invalidation
* on-demand computation

Idle Katalyst should be extremely cheap.

---

## 10. MEMORY IS A FIRST-CLASS CONSTRAINT
Always consider memory usage. Avoid:
* keeping entire repositories in memory
* duplicating transcripts
* duplicating large diffs
* unnecessary AST copies
* unnecessary serialized state
* retaining closed agent sessions forever

Large data should be streamed, paged, lazily loaded, cached selectively, and released when unused.

---

## 11. RENDER ONLY WHAT MATTERS
Do not render thousands of UI elements because the data exists. Virtualize large logs, transcripts, file lists, diffs, agent histories, and task lists. Avoid unnecessary reactive updates. A single agent event should not cause the entire application to re-render.

---

## 12. ANIMATION MUST SERVE INFORMATION
Animations should communicate: state transition, focus, hierarchy, progress. Never add animation merely because it looks cool. Prefer subtle transitions.  
Avoid:
* bouncing cards
* excessive spinners
* constant pulsing
* decorative motion
* animated dashboards

Codex/Zed-like calmness is the target.

---

## 13. KEYBOARD-FIRST
Power users should be able to operate Katalyst without constantly reaching for the mouse. Prioritize:
* command palette
* shortcuts
* quick agent switch
* quick task creation
* quick context insertion
* quick diff review
* quick approve/deny
* quick steer

Mouse interactions should remain excellent. Keyboard interactions should be exceptional.

---

## 14. INFORMATION HIERARCHY
Every screen should answer:
1. Where am I?
2. What is the agent doing?
3. What changed?
4. Is anything blocked?
5. What should I do next?

Do not make users search through panels to answer these questions.

---

## 15. ERROR UX
Errors must be understandable, actionable, recoverable. Avoid exposing raw panic, stack traces, JSON protocol errors, internal IDs, ACP internals, or MCP internals unless the user explicitly opens debug information.  
Prefer: *"Agent lost connection." [Reconnect]*  
rather than: *"ACP transport error: stream closed unexpectedly."*

---

## 16. FAILURE MUST BE GRACEFUL
* If an agent crashes: Katalyst should remain alive.  
* If MCP fails: the editor should remain usable.  
* If a model fails: the project should remain usable.  
* If network disappears: local editing should remain usable.  
* If one agent crashes: other agents should remain usable.  
Never allow one subsystem failure to take down the application.

---

## 17. LONG-RUNNING AGENTS
Agents may run for minutes or hours. Therefore:
* UI must remain responsive
* state must persist
* progress must be recoverable
* sessions must survive UI navigation
* logs should be streamable
* reconnecting must be safe
* restarting Katalyst should not unnecessarily destroy work

Treat agents as background workers, not temporary chat requests.

---

## 18. DO NOT OVER-ENGINEER
Do not create an abstraction just because another product has one. Before adding a subsystem ask:
* Can the existing architecture support this?
* Can this be a small adapter?
* Can OMP/ACP already solve it?
* Can Git already solve it?
* Can Zed already solve it?
* Can the feature be implemented incrementally?

Prefer the simplest architecture that satisfies the requirement.

---

## 19. MEASURE BEFORE CLAIMING
Do not claim "fast", "60 FPS", "low memory", "production ready", "Codex parity", or "Cursor parity" without evidence. When performance matters, measure:
* cold startup
* warm startup
* idle memory
* active memory
* typing latency
* scroll performance
* agent switching latency
* diff rendering latency
* repository indexing time
* CPU while idle
* CPU during agent streaming

Prefer actual measurements over assumptions.

---

## 20. EVERY FEATURE HAS A PERFORMANCE BUDGET
Before implementing a major feature, estimate: CPU impact, Memory impact, Startup impact, Disk impact, Network impact, and UI rendering impact. If the feature has no clear performance budget: DO NOT IMPLEMENT IT YET.

---

## 21. FEATURE PRIORITY
When choosing between features, use:
* **P0**: Stability, Performance, Core editing, Agent reliability, Data integrity
* **P1**: Agent workflow, Worktrees, Diff/review, Context, Steering, Permissions
* **P2**: Skills, MCP UX, Modes, Multi-agent orchestration
* **P3**: Remote/mobile, Design mode, Advanced automation
* **P4**: Nice-to-have features, Decorative UI, Analytics, Non-essential integrations

Never allow P3/P4 work to destabilize P0/P1.

---

## 22. THE "WOULD I WANT THIS OPEN ALL DAY?" TEST
Before shipping any UI change ask:
* If I am coding for 8 hours: Does this UI make me calmer or more distracted?
* Does it reduce friction or add friction?
* Does it help me understand my agents?
* Does it stay out of my way?
* Does it make the editor feel heavier?
* Would I want this visible all day?

If not: simplify it.

---

## 23. THE "CODEX FEEL" TEST
After every major UI change ask:  
Does it feel immediate? Quiet? Focused? Intentional? Stable? Predictable? Information-dense without being noisy?  
If the answer is no: **REDUCE. Do not add more UI.**

---

## 24. THE "NATIVE ZED" TEST
Katalyst is built on a native editor foundation. Do not fight that foundation. Whenever possible:
* reuse existing Zed patterns
* reuse existing GPUI primitives
* reuse existing editor infrastructure
* follow existing interaction conventions

Do not introduce web-style UI patterns merely because they are easier to implement.

---

## 25. FINAL RULE
When uncertain between:
A) more features  
B) better stability  
C) better performance  
D) simpler UX  

choose: **B, C, or D.**

A feature-rich Katalyst that feels heavy is a failure.  
A smaller Katalyst that feels **FAST, STABLE, NATIVE, CALM, and POWERFUL** is a success.

The ultimate objective is:
> **"Katalyst disappears and lets me code."**  

Not:
> *"Katalyst constantly reminds me that it has AI features."*

---

## NORTH STAR
Build Katalyst so that the user experiences:
```text
Zed's responsiveness
+
Cursor's coding flow
+
Codex's agent workflow
+
OMP's agent capabilities
```
while Katalyst itself remains:
**FAST • STABLE • QUIET • PREDICTABLE • NATIVE • LIGHTWEIGHT**

If a proposed improvement makes Katalyst objectively more capable but subjectively worse to use: **DO NOT SHIP IT. Optimize for the experience, not the feature count.**
