# Hypergraph Data Model for ChoirOS

> Synthesizing PNNL's HyperNetX research with ChoirOS requirements

---

## What We Just Did

You gave me a URL. I couldn't fetch it directly, but I searched and retrieved:
- HyperNetX documentation and JOSS paper (2024)
- Key publications from the PNNL team
- Author profiles (Cliff Joslyn, Brenda Praggastis, Sinan Aksoy, Emilie Purvine)
- Technical papers on hypergraph walks, s-connectivity, computational topology

This is exactly the workflow you imagined: URL → expand → research → integrate.

But I did it *manually*, in one session, with context limits. The recursive research problem is real—I could have gone deeper (every paper cites 30 more), but context would explode.

---

## What HyperNetX Is

A Python library from Pacific Northwest National Laboratory (PNNL) for hypergraph analysis.

**Key people:**
- **Cliff Joslyn** — Chief Knowledge Scientist at PNNL, PhD Systems Science (Binghamton), background in computational topology, cybernetics, general systems theory
- **Brenda Praggastis** — Principal developer, hypergraph algorithms
- **Sinan Aksoy** — High-order hypergraph walks, s-connectivity
- **Emilie Purvine** — Computational topology, sheaf theory

**Key concepts from their work:**

### 1. S-Walks (High-Order Hypergraph Walks)

In a graph, a walk is a sequence of edges where consecutive edges share a vertex.

In a hypergraph, edges can share *multiple* vertices. An **s-walk** requires consecutive edges to share at least s vertices.

```
s=1: edges share at least 1 vertex (weak connection)
s=2: edges share at least 2 vertices (stronger)
s=3: edges share at least 3 vertices (very tight coupling)
```

**Why this matters for ChoirOS:**

Citations aren't binary. "Article A cites Article B" is s=1. But "Article A deeply engages with Articles B, C, and D together on the same concept" is a higher-order relationship.

The citation *strength* can be represented as the s-value of the walk.

### 2. S-Components (Connected Components at Different Resolutions)

At s=1, the whole knowledge graph might be connected (everything cites something).

At s=5, it fragments into tight clusters—groups of artifacts that are deeply interrelated.

**Why this matters:**

Different views of the knowledge base. Zoomed out (s=1): everything connects. Zoomed in (s=5): only tight clusters visible.

### 3. Duality

Every hypergraph H has a dual H* where:
- Vertices of H become edges of H*
- Edges of H become vertices of H*

A vertex-walk on H is an edge-walk on H*.

**Why this matters:**

You can flip perspectives:
- "What artifacts share these authors?" (vertex-walk)
- "What authors share these artifacts?" (edge-walk on dual)

Same data, dual queries.

### 4. Incidence and Adjacency Matrices

For hypergraphs, these are not 0/1 matrices—they're weighted by intersection size.

The line graph L(H) has adjacency matrix S^T S (where S is the incidence matrix).

**Why this matters:**

Matrix operations give you efficient algorithms for:
- Finding connected components at each s
- Computing centrality (which artifacts are most central?)
- Detecting communities (clusters of related artifacts)

---

## Hypergraphs vs. Simplicial Complexes

HyperNetX connects to **computational topology** through simplicial complexes.

A simplicial complex is a hypergraph where:
- If an edge exists, all its subsets also exist
- (If {A,B,C} is an edge, then {A,B}, {A,C}, {B,C}, {A}, {B}, {C} are too)

Hypergraphs are more general—they don't require this closure property.

**For ChoirOS:**

We probably want general hypergraphs, not simplicial complexes. A citation doesn't imply all sub-citations exist.

But we *might* want to compute homology (topological invariants) on the knowledge base—and that's where simplicial complexes become useful.

---

## Recursive Research as Hypergraph Expansion

Your imagined workflow:

```
Input: URL with papers and names
       ↓
Expand: Read each paper
       ↓
Recurse: For each citation/author, expand again
       ↓
Integrate: Synthesize with existing knowledge
```

This IS hypergraph construction:

```
Initial hyperedge: { URL, Paper1, Paper2, Author1, Author2 }
       ↓
Expansion: For each node, add incident hyperedges
       ↓
Paper1 → { Paper1, Citation1, Citation2, Concept1 }
Author1 → { Author1, Paper1, Paper5, Institution1 }
       ↓
Continue until stopping condition
```

The result is a **hypergraph of knowledge** with:
- Nodes: papers, authors, concepts, institutions, datasets
- Hyperedges: relationships (citation, authorship, co-occurrence, etc.)

### The Context Explosion Problem

At depth 3, you have thousands of nodes. Can't fit in context.

**Solution: Hypergraph Compression**

Instead of expanding everything into flat context, build the hypergraph *structure* and query it.

```typescript
// Don't do this:
context = [paper1_fulltext, paper2_fulltext, ..., paper1000_fulltext]

// Do this:
hypergraph = {
  nodes: [paper1_id, paper2_id, ...],
  edges: [
    { id: 'cites_1', members: [paper1_id, paper2_id], type: 'citation' },
    { id: 'authors_1', members: [paper1_id, author1_id, author2_id], type: 'authorship' },
    ...
  ]
}

// Then query:
relevant_subgraph = hypergraph.s_neighborhood(query_node, s=2, depth=2)
context = fetch_content(relevant_subgraph.nodes)
```

The hypergraph is the *index*. You traverse it to select what goes into context.

---

## Applying to ChoirOS Data Model

### Nodes

```typescript
type NodeType = 
  | 'artifact'      // user files, documents
  | 'agent'         // AI agents
  | 'user'          // human users
  | 'concept'       // extracted concepts/topics
  | 'event'         // timestamps, actions
  | 'version'       // specific versions of artifacts
```

### Hyperedges

```typescript
interface Hyperedge {
  id: string;
  type: HyperedgeType;
  members: string[];        // node IDs
  timestamp: number;        // when this relationship was created
  weight?: number;          // strength of relationship
  metadata?: Record<string, unknown>;
}

type HyperedgeType =
  | 'citation'       // { citing_artifact, cited_artifact_1, ..., cited_artifact_n }
  | 'authorship'     // { artifact, author_1, ..., author_n }
  | 'edit'           // { artifact_v2, artifact_v1, editor, edit_intent }
  | 'merge'          // { merged_result, source_1, ..., source_n, merge_agent }
  | 'fanout'         // { parent_task, agent_1, ..., agent_n }
  | 'co_occurrence'  // { concept, artifact_1, ..., artifact_n }
  | 'session'        // { user, agent, start_time, artifacts_accessed... }
```

### Time and Versioning

Every hyperedge has a timestamp. The hypergraph is append-only.

"Current state" = replay all hyperedges up to now.
"State at time T" = replay up to T.
"History of artifact X" = all hyperedges containing X, ordered by time.

### Querying

Using HyperNetX concepts:

```python
# Find artifacts strongly connected to artifact X (s=2 means share 2+ common citations)
neighbors = H.s_neighbors(X, s=2)

# Find connected components at s=3 (tight clusters)
components = H.s_components(s=3)

# Compute centrality (which artifacts are most connected?)
centrality = H.s_betweenness_centrality(s=1)

# Get the dual: flip to author-centric view
H_dual = H.dual()
```

---

## Integration with Existing Decisions

### D13 (Updated): Hypergraph Data Model

The underlying data structure is a hypergraph implemented using HyperNetX concepts:

**Nodes:** artifacts, agents, users, concepts, events, versions

**Hyperedges:** N-ary relationships with types (citation, authorship, edit, merge, fanout, co-occurrence)

**Time:** Every hyperedge has a timestamp. Append-only log. State computed by replay.

**Queries:** S-walks for connectivity at different strengths. S-components for clustering. Duality for perspective flipping.

**Storage:** Event log (NATS JetStream) as source of truth. Hypergraph structure materialized in-memory or SQLite for queries. HyperNetX for analysis.

### New Capabilities

1. **S-filtered views**: Show only strong connections (high s) or all connections (s=1)

2. **Dual views**: Flip between artifact-centric and author-centric views

3. **Topological analysis**: Detect holes (missing connections), compute homology

4. **Community detection**: Find clusters using hypergraph modularity algorithms

5. **Centrality**: Which artifacts/authors are most important?

---

## Recursive Research Implementation

```python
async def recursive_research(
    seed_url: str,
    max_depth: int = 3,
    s_threshold: int = 2,
    max_nodes: int = 1000
) -> Hypergraph:
    """
    Expand from a seed URL into a knowledge hypergraph.
    Uses s-connectivity to prune weak connections.
    """
    H = Hypergraph()
    queue = [(seed_url, 0)]  # (url, depth)
    
    while queue and len(H.nodes) < max_nodes:
        url, depth = queue.pop(0)
        
        if depth > max_depth:
            continue
            
        # Fetch and extract
        content = await fetch(url)
        entities = extract_entities(content)  # papers, authors, concepts
        
        # Add to hypergraph
        for entity in entities:
            H.add_node(entity.id, **entity.metadata)
        
        # Add hyperedge for this document
        H.add_edge(
            members=[e.id for e in entities],
            type='document',
            source=url,
            timestamp=now()
        )
        
        # Queue expansion for highly-connected nodes
        for node in H.nodes:
            if H.degree(node, s=s_threshold) > threshold:
                # This node is well-connected, worth expanding
                expansion_urls = get_expansion_urls(node)
                for exp_url in expansion_urls:
                    if exp_url not in visited:
                        queue.append((exp_url, depth + 1))
    
    return H
```

The key insight: **s-connectivity guides pruning**. Don't expand weakly-connected nodes.

---

## What This Enables

### For the ? Bar

```
User: "research hypergraphs deeply, integrate with what we know about ChoirOS"

Agent:
1. Seed: user's query → initial search
2. Expand: recursively fetch papers, authors, concepts
3. Build: hypergraph of knowledge
4. Prune: use s-connectivity to focus on strong relationships
5. Query: find nodes most central to both "hypergraphs" AND "ChoirOS"
6. Synthesize: generate artifact from relevant subgraph
7. Cite: hyperedges become citations in output
```

### For the Knowledge Base

The citation economy becomes a hypergraph economy:
- Artifacts are nodes
- Citations are hyperedges (can cite multiple sources in one edge)
- S-centrality determines importance
- Rewards flow through hyperedge structure

### For Agent Coordination

Fanout is a hyperedge: { result, agent_1_output, ..., agent_n_output }

The merge isn't pairwise—it's N-ary. All agents contribute to one hyperedge.

---

## References

**Core HyperNetX Papers:**

1. Praggastis et al. (2024) "HyperNetX: A Python package for modeling complex network data as hypergraphs" — JOSS paper, library overview

2. Aksoy et al. (2020) "Hypernetwork Science via High-Order Hypergraph Walks" — s-walks, s-connectivity, foundational algorithms

3. Joslyn et al. (2021) "Hypernetwork Science: From Multidimensional Networks to Computational Topology" — theoretical overview, connection to topology

4. Feng et al. (2021) "Hypergraph models of biological networks to identify genes critical to pathogenic viral response" — application to biology

5. Joslyn et al. (2020) "Hypergraph Analytics of Domain Name System Relationships" — application to cybersecurity

**Key People:**

- Cliff Joslyn (PNNL) — Chief Knowledge Scientist, systems theory + topology
- Brenda Praggastis (PNNL) — Principal developer
- Sinan Aksoy (PNNL) — High-order walks
- Emilie Purvine (PNNL) — Computational topology

**Related Tools:**

- XGI (CompleX Group Interactions) — Alternative Python hypergraph library
- Chapel HyperGraph Library (CHGL) — High-performance backend for HyperNetX

---

*This document demonstrates the recursive research workflow—seed URL expanded into structured knowledge integrated with existing project context.*
