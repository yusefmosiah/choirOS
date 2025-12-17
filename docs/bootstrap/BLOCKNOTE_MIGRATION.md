# BlockNote Migration Instructions

> Instructions for migrating the Writer app from TipTap to BlockNote.

---

## Goal

Replace the TipTap-based Writer app with BlockNote to achieve:
1. **Notion-like block-based editing** — drag/drop blocks, nested content
2. **`?` commands** — slash menu triggered by `?` instead of `/`
3. **No formatting toolbar** — rely on slash menu and inline formatting
4. **Easy media embedding** — images, video, audio via slash menu

---

## Current State

### Files to Modify/Replace

| File | Action | Notes |
|------|--------|-------|
| `src/components/apps/Writer.tsx` | **Replace** | Swap TipTap for BlockNote |
| `src/components/apps/WriterToolbar.tsx` | **Delete** | No toolbar needed |
| `src/components/apps/WriterToolbar.css` | **Delete** | Empty file |
| `src/components/apps/Writer.css` | **Modify** | Update for BlockNote classes |
| `package.json` | **Modify** | Swap dependencies |

### Current Dependencies to Remove

```json
"@tiptap/extension-placeholder": "^3.13.0",
"@tiptap/react": "^3.13.0",
"@tiptap/starter-kit": "^3.13.0"
```

### New Dependencies to Add

```json
"@blocknote/core": "^0.22.0",
"@blocknote/react": "^0.22.0",
"@blocknote/mantine": "^0.22.0"
```

> **Note:** BlockNote uses Mantine for default styling. Check [latest versions](https://www.npmjs.com/package/@blocknote/react) before installing.

---

## Step-by-Step Instructions

### Step 1: Update Dependencies

```bash
cd /Users/wiz/choirOS/choiros

# Remove TipTap
npm uninstall @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder

# Install BlockNote
npm install @blocknote/core @blocknote/react @blocknote/mantine
```

### Step 2: Delete Obsolete Files

```bash
rm src/components/apps/WriterToolbar.tsx
rm src/components/apps/WriterToolbar.css
```

### Step 3: Replace Writer.tsx

Create new `src/components/apps/Writer.tsx`:

```tsx
// Writer App - BlockNote-based block editor
import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import { SuggestionMenuController, getDefaultReactSlashMenuItems } from "@blocknote/react";
import './Writer.css';

interface WriterProps {
    artifactId?: string;
}

export function Writer({ artifactId }: WriterProps) {
    // Create editor instance
    const editor = useCreateBlockNote({
        // Initial content - will load from artifact in Phase 4
        initialContent: artifactId ? undefined : undefined,
    });

    // Custom slash menu items (can extend later)
    const getMenuItems = (query: string) => {
        return getDefaultReactSlashMenuItems(editor).filter((item) =>
            item.title.toLowerCase().includes(query.toLowerCase())
        );
    };

    return (
        <div className="writer">
            <BlockNoteView
                editor={editor}
                slashMenu={false}  // Disable default "/" trigger
                theme="dark"
                onChange={() => {
                    // Debounced auto-save will come in Phase 4
                    console.log('[Writer] Content updated');
                }}
            >
                {/* Custom "?" triggered menu */}
                <SuggestionMenuController
                    triggerCharacter="?"
                    getItems={async (query) => getMenuItems(query)}
                />
            </BlockNoteView>
        </div>
    );
}
```

### Step 4: Update Writer.css

Replace `src/components/apps/Writer.css` with BlockNote-compatible styles:

```css
/* Writer App Styles - BlockNote */
.writer {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
    overflow: hidden;
}

/* BlockNote container */
.writer .bn-container {
    height: 100%;
    background: var(--bg-primary);
}

/* Editor area */
.writer .bn-editor {
    padding: var(--spacing-md);
    color: var(--text-primary);
}

/* Override BlockNote theme colors to match ChoirOS theme */
.writer [data-theming-css-variables-demo] {
    --bn-colors-editor-background: var(--bg-primary);
    --bn-colors-editor-text: var(--text-primary);
    --bn-colors-menu-background: var(--bg-secondary);
    --bn-colors-menu-text: var(--text-primary);
    --bn-colors-tooltip-background: var(--bg-tertiary);
    --bn-colors-tooltip-text: var(--text-primary);
    --bn-colors-hovered-background: var(--bg-tertiary);
    --bn-colors-selected-background: var(--accent-gold-dim);
    --bn-colors-side-menu: var(--text-secondary);
}

/* Suggestion menu (? commands) */
.writer .bn-suggestion-menu {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.writer .bn-suggestion-menu-item {
    color: var(--text-primary);
}

.writer .bn-suggestion-menu-item:hover,
.writer .bn-suggestion-menu-item[data-highlighted] {
    background: var(--bg-tertiary);
}

/* Block styling */
.writer .bn-block {
    margin: 0.5em 0;
}

/* Headings */
.writer h1 {
    font-size: 2em;
    font-weight: 700;
    color: var(--text-primary);
}

.writer h2 {
    font-size: 1.5em;
    font-weight: 600;
    color: var(--text-primary);
}

.writer h3 {
    font-size: 1.25em;
    font-weight: 600;
    color: var(--text-primary);
}

/* Placeholder text */
.writer [data-placeholder]::before {
    color: var(--text-secondary);
}

/* Selection */
.writer ::selection {
    background: var(--accent-gold);
    color: var(--bg-primary);
}

/* Code blocks */
.writer pre {
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
}

.writer code {
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
    padding: 0.1em 0.4em;
    font-family: var(--font-mono);
    color: var(--accent-gold);
}

/* Blockquote */
.writer blockquote {
    border-left: 3px solid var(--accent-gold-dim);
    padding-left: var(--spacing-md);
    color: var(--text-secondary);
    font-style: italic;
}

/* Hide default toolbar (we're using ? commands only) */
.writer .bn-formatting-toolbar {
    display: none;
}
```

### Step 5: Verify the Build

```bash
npm run dev
```

Test the following:
1. Open Writer app from desktop
2. Type `?` to trigger the command menu
3. Select "Heading" or "Bullet List" from menu
4. Verify blocks can be dragged and reordered
5. Verify text formatting (bold/italic) works with keyboard shortcuts (Cmd+B, Cmd+I)

---

## Future Enhancements

### Video Support

BlockNote includes a built-in `video` block for direct video files (MP4, WebM, etc.). This works out of the box via the `?` menu → "Video".

**For YouTube/Vimeo embeds**, create a custom block:

```tsx
// src/lib/blocks/EmbedBlock.tsx
import { createReactBlockSpec } from "@blocknote/react";

export const EmbedBlock = createReactBlockSpec(
    {
        type: "embed",
        propSchema: {
            url: { default: "" },
        },
        content: "none",
    },
    {
        render: (props) => {
            const url = props.block.props.url;
            const embedUrl = getEmbedUrl(url);

            return (
                <div className="embed-block" contentEditable={false}>
                    {embedUrl ? (
                        <iframe
                            src={embedUrl}
                            width="100%"
                            height="315"
                            frameBorder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                        />
                    ) : (
                        <input
                            type="text"
                            placeholder="Paste YouTube/Vimeo URL..."
                            onBlur={(e) => {
                                props.editor.updateBlock(props.block, {
                                    props: { url: e.target.value },
                                });
                            }}
                        />
                    )}
                </div>
            );
        },
    }
);

// Convert YouTube/Vimeo URLs to embed format
function getEmbedUrl(url: string): string | null {
    if (!url) return null;

    // YouTube
    const ytMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&]+)/);
    if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}`;

    // Vimeo
    const vimeoMatch = url.match(/vimeo\.com\/(\d+)/);
    if (vimeoMatch) return `https://player.vimeo.com/video/${vimeoMatch[1]}`;

    return null;
}
```

Add to schema and `?` menu:

```tsx
// In Writer.tsx
import { EmbedBlock } from "../lib/blocks/EmbedBlock";
import { Video } from "lucide-react";

const schema = BlockNoteSchema.create({
    blockSpecs: { ...defaultBlockSpecs, embed: EmbedBlock },
});

// Add to menu items
{
    title: "YouTube / Embed",
    group: "Media",
    icon: <Video size={18} />,
    onItemClick: () => {
        editor.insertBlocks(
            [{ type: "embed", props: { url: "" } }],
            editor.getTextCursorPosition().block,
            "after"
        );
    },
    aliases: ["youtube", "vimeo", "embed", "video"],
    subtext: "Embed a YouTube or Vimeo video",
}
```

### Custom Block Types

Add custom blocks for media embedding:

```tsx
// src/lib/blocks/AudioBlock.tsx
import { createReactBlockSpec } from "@blocknote/react";

export const AudioBlock = createReactBlockSpec(
    {
        type: "audio",
        propSchema: {
            src: { default: "" },
            title: { default: "" },
        },
        content: "none",
    },
    {
        render: (props) => (
            <div className="audio-block">
                <audio controls src={props.block.props.src}>
                    {props.block.props.title}
                </audio>
            </div>
        ),
    }
);
```

### Adding Custom Blocks to Schema

```tsx
import { BlockNoteSchema, defaultBlockSpecs } from "@blocknote/core";
import { AudioBlock } from "../lib/blocks/AudioBlock";

const schema = BlockNoteSchema.create({
    blockSpecs: {
        ...defaultBlockSpecs,
        audio: AudioBlock,
    },
});

// Use in editor
const editor = useCreateBlockNote({ schema });
```

### Adding Custom ? Menu Items

```tsx
const customMenuItems = [
    ...getDefaultReactSlashMenuItems(editor),
    {
        title: "Audio",
        group: "Media",
        icon: <Music size={18} />,
        onItemClick: () => {
            editor.insertBlocks(
                [{ type: "audio", props: { src: "", title: "New Audio" } }],
                editor.getTextCursorPosition().block,
                "after"
            );
        },
        aliases: ["audio", "music", "sound"],
        subtext: "Embed an audio file",
    },
];
```

---

## Rollback Plan

If issues arise, restore TipTap:

```bash
npm uninstall @blocknote/core @blocknote/react @blocknote/mantine
npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder
git checkout -- src/components/apps/Writer.tsx src/components/apps/Writer.css
git checkout -- src/components/apps/WriterToolbar.tsx src/components/apps/WriterToolbar.css
```

---

## References

- [BlockNote Docs](https://www.blocknotejs.org/docs)
- [BlockNote GitHub](https://github.com/TypeCellOS/BlockNote)
- [Customizing Suggestion Menus](https://www.blocknotejs.org/docs/ui-components/suggestion-menus)
- [Custom Block Types](https://www.blocknotejs.org/docs/custom-schemas/custom-blocks)
- [Theming](https://www.blocknotejs.org/docs/styling-theming)
