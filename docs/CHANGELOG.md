# Changelog

## [2025-12-17] - choirOS Desktop v0 (Phase 2: Sources Workflow)

### Added

- **FastAPI Backend** (`/api`):
  - YouTube transcript parser (youtube-transcript-api, yt-dlp)
  - Web page parser (Trafilatura)
  - Document parser (MarkItDown - PDF, DOCX, PPTX, images, audio)
  - In-memory artifact store
  - CORS configured for local dev (ports 5173, 5174)

- **Files App:** Unified file browser for `/sources` folder
  - Lists parsed artifacts with icons by type (🎬 YouTube, 🌐 Web, 📄 Upload)
  - Double-click to open in Writer with full content
  - Delete and external link actions

- **Taskbar Enhancements:**
  - URL detection in ? bar — paste URL to parse
  - ? menu → "Upload Files" button for document parsing
  - Toast notifications with click-to-open
  - Duplicate URL detection with Cancel/Overwrite/Keep Both dialog

- **Writer App:**
  - Loads artifact content when opened with `artifactId` prop
  - Scroll support fixed for long documents
  - Title bar shows source name

- **API Client & Store:**
  - `lib/api.ts` — typed fetch wrappers for all endpoints
  - `stores/sources.ts` — Zustand store for artifacts

### Changed

- Removed separate "Sources" app — unified into Files
- Desktop icons: Files, Writer, Terminal

### Technical Details

- **New Dependencies:** FastAPI, Uvicorn, Pydantic, youtube-transcript-api, yt-dlp, trafilatura, markitdown, python-multipart, httpx
- **Dev Script:** `./dev.sh` runs frontend + backend concurrently

---

## [2025-12-16] - choirOS Desktop v0 (Phase 1.1: BlockNote Migration)

### Changed

- **Writer App:** Migrated from TipTap to BlockNote rich text editor
  - Block-based editing with drag/drop reordering
  - Custom `?` command trigger (instead of `/`) for brand consistency
  - Removed formatting toolbar (relying on `?` menu and keyboard shortcuts)
  - Localized placeholder text to show `?` hint

### Removed

- `WriterToolbar.tsx` and `WriterToolbar.css` (no longer needed)

---

## [2025-12-16] - choirOS Desktop v0 (Phase 1: Static Shell)

### Added

- **Desktop Shell:** Built complete web desktop environment from scratch using Vite + React + TypeScript
  - Desktop surface with gradient wallpaper and icon grid
  - Taskbar with ? command input, running apps tray, and menu button
  - Desktop icons for Writer, Files, and Terminal apps

- **Window Manager:** Zustand-based window state management
  - Open, close, focus, minimize, maximize windows
  - Drag and resize windows (mouse and touch)
  - Cascading window positions with z-index management
  - Viewport-responsive sizing (phone/tablet/desktop breakpoints)

- **Writer App:** TipTap-based rich text editor
  - Formatting toolbar (bold, italic, headings, lists, blockquote, code)
  - Placeholder text and content change logging
  - Wrapping toolbar for mobile viewports

- **Mobile Feature Parity:**
  - Touch drag support for window title bars
  - Touch resize support via visible grip in bottom-right corner
  - Double-tap to open apps on touch devices
  - Responsive window sizing: 95% width / 92% height on phones, 70%/65% on tablets

- **CSS Architecture:**
  - CSS custom properties for theming ("Carbon Fiber Kintsugi" theme)
  - Minimal CSS reset and global styles
  - App and component-scoped stylesheets

- **Static Artifacts:**
  - `public/artifacts/system/theme.json` - Theme configuration
  - `public/artifacts/system/apps.json` - App registry

### Technical Details

- **Stack:** Vite 7, React 18, TypeScript, Zustand, TipTap, Lucide React, dnd-kit
- **Project Structure:** Following `docs/bootstrap/STACK.md` conventions
- **Exit Criteria Met:** Per `docs/bootstrap/PHASES.md` Phase 1

---

## [2025-12-11] - 2025-12-11

### Sunset: Tuxedo → choirOS Transition

This entry marks the sunsetting of the Tuxedo codebase as development moves to choirOS.

**Update (2025-12-11):** The initial plan was to fork DaedalOS. After evaluation, decided to build the web desktop from scratch using Vite + React + TypeScript, with daedalOS code as reference material only. Key architectural choices: NATS JetStream event bus, Firecracker microVMs for agent isolation, per-user SQLite synced to S3, Qdrant for vectors. See `docs/choiros-bootstrap/` for the full architecture.

### The Journey Through Tuxedo

**Origins (Fall 2024):**

- Started as a yield farming agent for Stellar blockchain hackathon
- Built on Stellar Scaffold with DeFindex integration
- Goal: AI-optimized DeFi yield strategies

**The Pivot (Late 2024 - Early 2025):**

- Kept drifting back toward Choir's core vision
- Yield farming was the costume; Choir was the body underneath
- Realized narrow agents (yield farming, ghostwriting) share isomorphic capabilities

**Context Engineering Revelation:**

- Key insight: Narrow agents don't scale because they lack their own environment
- A specialized agent ≈ general agent + specialized context
- Instead of N agents for N domains → one capable agent + N workspaces
- The prompt, tools, files, and history create specialization at runtime, not training time

**Architecture Exploration:**

- LangGraph: Graph-based workflow orchestration (too rigid)
- MCP: Service-oriented phase servers (added complexity without benefit)
- Qdrant-Sui MVP: Vector search + blockchain primitives (right blocks, unclear agent-environment relationship)
- Conductor + Agents: Client-side orchestration with server-side specialized agents (getting closer)

**The Automatic Computer Thesis Emerges:**

- The computer itself should be the agent's environment
- Not a chatbot to talk to, but an intelligent computational substrate
- Pansynchronous operation: instant to indefinite timescales
- Observable: agents watch file changes, app events, user actions
- File-as-memory: agents write to files, files ARE the state

### The choirOS Decision

**Why fork DaedalOS:**

- Mobile responsive (works fast on phones/tablets)
- MIT license (maximum freedom)
- No business conflict (solo dev project, no platform lock-in)
- Fork-as-distribution model (every workspace is marketing)
- Rich foundation: file system, terminal, editors, WebLLM, browser—all working

**What carries forward:**

- From Choir: Citation graph, deposit economics, CHOIR token on Sui mainnet
- From Tuxedo: Context engineering principles, file-as-memory, pansynchronous operation
- From DaedalOS: Web desktop environment, mobile-responsive UI, fork-as-distribution

**What's new in choirOS:**

- Vibe-design as onboarding (prompt-based theming teaches the paradigm)
- Relationship-based permissions (spouse sees all, doctor sees medical, stranger sees bio)
- SQLite + S3 per-user state architecture
- Custom domains as identity (alice.computer)

### What Tuxedo Accomplished

- Proved multi-agent orchestration patterns
- Developed Ghostwriter pipeline with citation verification
- Explored MCP, LangGraph, and conductor architectures
- Identified the gap between narrow agents and general-purpose agent environments
- Crystallized the automatic computer thesis through iterative architecture exploration

### References

- [choir_evolution_narrative.md](./choir_evolution_narrative.md) - Full prose narrative of the transitions
- [agentic_computer_paradigm.md](./agentic_computer_paradigm.md) - The paradigm thesis document
- [agentic_computer_vision.md](./agentic_computer_vision.md) - Implementation vision for choirOS
- [agentic_computer_position_paper.md](./agentic_computer_position_paper.md) - Position paper on pansynchronous computing

---

## [2025-08-18] - 2025-08-18

### Added

- Company incorporation: Choir Harmonic Intelligence Platform, Inc. (CHI) formed in early May 2025
- TestFlight beta launch (early May 2025); shared with early users for feedback
- Conductor + Instruments (Agents) architecture: client-side Conductor orchestrating server agents (Ghostwriter, Publisher, Revision)
- Privacy-first Conductor: planning to run Conductor in Phala Network TEE with GPU LLM for private inference and orchestration

### Changed

- Product/positioning pivot: from “new kind of social media” to “the language game for the learning economy” focused on conversation-to-publication with citations and rewards
- Execution focus narrowed: 80/20 on Ghostwriter writing agent (research/drafting/citation) instead of “do everything”
- Economics updated:
  - Credits (IAP-compliant) gate Ghostwriter compute; no subscription plans
  - Tokens issued only on Ghostwriter invocations (not per prompt)
  - Publication investment (pay to publish; ranking by spend)
  - Revision markets (stake to propose revisions; accepted → co-authorship; split decisions route to Treasury)
  - Citation rewards currently 5 tokens per citation; treasury-based scaling planned
- Architecture/docs migration: deprecated PostChain/AEIOU terminology in favor of Conductor + Agents across content and docs
- Provider updates: add AWS Bedrock; remove Fireworks

### Feedback Summary (May–Aug 2025)

- Mixed feedback on beta: strong resonance with the idea (+), concerns about execution and clarity (–)
- Action: simplified onboarding/messaging and refocused feature set to clarify “what Choir is” and “how to use it”

### Notes

- Mainnet status unchanged: CHOIR live on Sui mainnet
- Wallet-based identity with anonymity by default; attribution on publish

## [2025-04-28] - 2025-04-28

### Added

- **Mainnet Deployment:** Successfully deployed Choir to the Sui mainnet with package ID `0x4f83f1cd85aefd0254e5b6f93bd344f49dd434269af698998dd5f4baec612898::choir::CHOIR`.
- **Multiple Wallet Support:** Implemented support for multiple wallet accounts with horizontal scrolling in the Wallets tab.
- **Wallet & Thread Import/Export:** Added secure import and export functionality for wallets and threads with biometric protection.
- **Rewards System:** Implemented the full rewards system with:
  - **Novelty Rewards:** Users earn rewards for original content based on vector similarity scores.
  - **Citation Rewards:** Authors of cited content receive rewards when their contributions inform responses.
  - **Choir Coin Integration:** Connected to Sui blockchain for minting and distributing CHOIR tokens.
- **Improved Pagination:** Enhanced pagination system that preserves formatting across pages while maximizing content density.
- **Transaction Management:** Added a dedicated Transactions tab showing a chronological history of all transactions across wallets.
- **Citation Display:** Implemented early UI for displaying and interacting with citations in vector content.
- **Performance Optimization:** Improved app launch and navigation performance by loading only thread metadata initially and loading full content when needed.
- **Model Updates:** Added support for newer AI models and improved model configuration management.

### Changed

- **UI Redesign:** Completely redesigned interface with improved navigation flow and visual consistency.
- **Thread Management:** Enhanced thread persistence with wallet-specific thread storage and optimized loading.
- **Authentication Flow:** Improved authentication with biometric support (FaceID/TouchID) and passcode fallback.

## [2025-04-09] - 2025-04-09

### Added

- **iOS Client Persistence:** Implemented local JSON file storage for thread data.
- **Automatic Thread Titles:** Threads now get an auto-generated title based on the first 10 words of the initial AI Action phase response.
- **Close the Loop UI:** When the yield phase finishes downloading, if the user is viewing the action phase, the UI now automatically transitions to display the final response with a smooth wrap-around animation.

## [2025-03-28] - 2025-03-28

### Added

- **PostChain Sequential Model Execution:** Implemented a prototype version of the PostChain running on a mobile device, successfully executing a sequence of 6 distinct AI models. This demonstrates the feasibility of the multi-phase workflow and shows initial promise for value generation.

### Changed

- **Architectural Validation:** The sequential model execution validates the core concept of the PostChain flow. Next steps involve implementing background looping, Qdrant database integration for state persistence and memory, and connecting to the Sui service for reward distribution. These are considered tractable integration tasks.

## [2025-03-27] - 2025-03-27

### Changed

- **Architectural Focus Shift: Qdrant-Sui MVP Prioritized**
  - Refocused development efforts on a Minimum Viable Product (MVP) centered around **Qdrant** (data/vector store) and **Sui** (blockchain token/rewards).
  * Adopted a streamlined architecture using the existing **Python API (FastAPI)** as the central orchestrator.
  * Leveraging the current **LCEL-based PostChain workflow** (`langchain_workflow.py`) for MVP implementation speed.
  * Defined clear data structures and interactions between the API, PostChain phases, Qdrant collections (`choir`, `users`, `chat_threads`, `intention_memory`, `observation_memory`), and the `sui_service.py`.
  * Refined core documentation (`core_core.md`, `state_management_patterns.md`, `blockchain_integration.md`, `security_considerations.md`, `stack_argument.md`, `index.md`) to reflect the MVP scope and architecture.

### Deferred (Post-MVP)

- Implementation of the full Model Context Protocol (MCP) server architecture.
- Integration of client-side libSQL caching for offline support.
- Deployment using Phala Network TEEs for confidential computing.
- Implementation of the full dynamic economic model (MVP uses basic rewards).

## [Unreleased] - 2025-03-12

### Changed

- **Major Architectural Pivot: Shifted from LangGraph to MCP Architecture**
  - Transitioned to Model Context Protocol (MCP) architecture for the Choir platform.
  - Adopted a service-oriented architecture with each PostChain phase implemented as a separate MCP server.
  - Implemented MCP Resources for efficient conversation state management and context sharing.
  - Leveraged MCP Notifications for real-time updates and communication between Host and Servers.
  - Replaced LangGraph-based workflow orchestration with a Host-application-centric orchestration model using asynchronous tasks.
  - Refined the focus on modularity, scalability, and security through the MCP architecture.

### Added

- **Coherent Technology Stack for MCP Architecture:**
  - **Model Context Protocol (MCP) Architecture:** Service-oriented architecture for PostChain phases, enabling modularity and scalability.
  - **PySUI:** Maintained PySUI for blockchain integration and economic actions.
  - **Pydantic:** Continued use of Pydantic for type safety and message validation in the MCP architecture.
  - **FastAPI/Uvicorn:** Continued use of FastAPI/Uvicorn for the Python API layer, now orchestrating MCP server interactions.
  - **Docker:** Maintained Docker for containerization and deployment of MCP servers.
  - **Phala Network:** Maintained Phala Network for TEE-secured operations and confidential computing for MCP servers.

- **Enhanced Token Economy and Reward System (RL-Driven CHOIR):**
  - **CHOIR Coins as Training Signals for AI:** Evolved the CHOIR coin to act as training signals for AI models, driving a self-improving AI ecosystem.
  - **Novelty and Citation Rewards:** Implemented novelty rewards for original prompts and citation rewards for salient contributions, algorithmically distributed by AI models.
  - **Contract as Data Marketplace Foundation:** Defined the contract as the basis for a data marketplace within Choir, enabling CHOIR-based data access and contribution pricing.
  - **Data Economy Vision:** Developed the vision for a comprehensive data marketplace where CHOIR serves as the currency for accessing and contributing to valuable datasets.

### Removed

- Deprecated LangGraph dependency and graph-based state management due to scalability and maintenance concerns.

## [2025-02-25] - 2025-02-25

### Added

- Implemented UI carousel to improve user experience
- Added display of priors in the Experience step
- Resumed active development after coding hiatus

### Planned

- API streaming implementation to enhance responsiveness
- Model reconfiguration for improved performance
- Go multimodel, then multimodal
- OpenRouter integration
- Conceptual evolution from "Chorus Cycle" to "Post Chain"
  - Representing shift from harmonic oscillator (cycle) to anharmonic oscillator (chain)
  - Aligning interface terminology with underlying model
- Client-side editable system prompts for customization
- Additional phases in the Post Chain:
  - Web search phase for real-time information access
  - Sandboxed arbitrary tool use phase for enhanced capabilities

## [2025-02-24] - 2025-02-24

### Changed

- Implemented fractional quantum anharmonic oscillator model for dynamic stake pricing
- Added fractional parameter α to capture memory effects and non-local interactions
- Revised parameter modulation formulas for K₀, α, and m to reflect interdependencies
- Created simulation framework for parameter optimization

## [2025-02-23] - 2025-02-23

### Changed

- Documented quantum anharmonic oscillator model implementation and dynamic stake pricing mechanism via an effective anharmonic coefficient modulated by approval/refusal statistics.

## [Unreleased]

### Changed

- Updated all documentation to version 6.0
  - Transformed structured documentation into fluid prose
  - Relaxed event-driven architecture requirements for initial TestFlight
  - Clarified implementation priorities and post-funding features
  - Maintained theoretical frameworks while focusing on core functionality

### Added

- Initial Chorus cycle working in iOS simulator
  - Basic message flow through phases
  - Response handling
  - State management

### Documented

- Created 15 comprehensive issues covering:
  - Core message system implementation
  - Type reconciliation with Qdrant
  - API client updates
  - Coordinator message flow
  - User identity management
  - Thread state management
  - Integration testing
  - Error handling strategy
  - Performance monitoring
  - State recovery
  - Thread sheet implementation
  - Thread contract implementation
  - Message rewards system
  - LanceDB migration
  - Citation visualization

### Architecture

- Defined clear type system for messages
- Planned migration to LanceDB
- Structured multimodal support strategy

### Technical Debt

- Identified areas needing more specification:
  - Thread Sheet UI (marked as "AI SLOP")
  - Reward formulas need verification
  - Migration pipeline needs careful implementation

## [0.4.2] - 2024-11-09

### Added

- Development principles with focus on groundedness
- Basic chat interface implementation
- SwiftData message persistence // this subsequently became a problem. swiftdata is coupled with swiftui and there was interference between view rendering and data persistence
- Initial Action step foundation

### Changed

- Shifted to iterative, ground-up development approach
- Simplified initial implementation scope
- Focused on working software over theoretical architecture
- Adopted step-by-step Chorus Cycle implementation strategy

### Principles

- Established groundedness as core development principle
- Emphasized iterative growth and natural evolution
- Prioritized practical progress over theoretical completeness
- Introduced flexible, evidence-based development flow

## [0.4.1] - 2024-11-08

### Added

- Self-creation process
- Post-training concepts
- Concurrent processing ideas
- Democratic framing
- Thoughtspace visualization

### Changed

- Renamed Update to Understanding
- Enhanced step descriptions
- Refined documentation focus
- Improved pattern recognition

## [0.4.0] - 2024-10-30

### Added

- Swift architecture plans
- Frontend-driven design
- Service layer concepts
- Chorus cycle definition

### Changed

- Enhanced system architecture
- Refined core patterns

## [0.3.5] - 2024-09-01

- Choir.chat as a web3 dapp
- messed around with solana
- used a lot of time messing with next.js/react/typescript/javascript
- recognized that browser extension wallet is terrible ux

## [0.3.0] - 2024-03-01

### Added

- ChoirGPT development from winter 2023 to spring 2024

- First developed as a ChatGPT plugin, then a Custom GPT
- The first global RAG system / collective intelligence as a GPT

## [0.2.10] - 2023-04-01

### Added

- Ahpta development from winter 2022 to spring 2023

## [0.2.9] - 2022-04-01

### Added

- V10 development from fall 2021 to winter 2022

## [0.2.8] - 2021-04-01

### Added

- Elevisio development from spring 2020 to spring 2021

## [0.2.7] - 2020-04-01

### Added

- Bluem development from spring 2019 to spring 2020

## [0.2.6] - 2019-04-01

### Added

- Blocstar development from fall 2018 to spring 2019

## [0.2.5] - 2018-04-01

### Added

- Phase4word development from summer 2017 to spring 2018

### Changed

- Showed Phase4word to ~50 people in spring 2018, received critical feedback
- Codebase remains in 2018 vintage

## [0.2.0] - 2016-06-20

### Added

- Phase4 party concept
- Early democracy technology
- Initial value systems

### Changed

- Moved beyond truth measurement framing
- Refined core concepts

## [0.1.0] - 2015-07-15

### Added

- Initial simulation hypothesis insight
- "Kandor"
- Quantum information concepts
- Planetary coherence vision
- Core system ideas
