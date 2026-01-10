// Mail App - Email client
import { useState } from 'react';
import { Mail, Inbox, Send, Star, Trash2, Archive, PenSquare, Search, Paperclip, Reply, Forward, MoreHorizontal } from 'lucide-react';
import './Mail.css';

interface Email {
    id: string;
    from: string;
    fromEmail: string;
    to: string;
    subject: string;
    preview: string;
    body: string;
    date: Date;
    read: boolean;
    starred: boolean;
    folder: 'inbox' | 'sent' | 'starred' | 'trash' | 'archive';
    hasAttachment?: boolean;
}

const SAMPLE_EMAILS: Email[] = [
    {
        id: '1',
        from: 'Alice Chen',
        fromEmail: 'alice@example.com',
        to: 'me@choiros.local',
        subject: 'Project Update - Q4 Goals',
        preview: 'Hi! I wanted to follow up on our discussion about the Q4 roadmap...',
        body: `Hi!

I wanted to follow up on our discussion about the Q4 roadmap. Here are the key points we need to address:

1. Feature completion for the new dashboard
2. Performance optimization targets
3. User feedback integration

Let me know when you're free to discuss further.

Best,
Alice`,
        date: new Date(Date.now() - 1000 * 60 * 30),
        read: false,
        starred: true,
        folder: 'inbox',
        hasAttachment: true,
    },
    {
        id: '2',
        from: 'Bob Martinez',
        fromEmail: 'bob@example.com',
        to: 'me@choiros.local',
        subject: 'Re: Meeting Tomorrow',
        preview: 'Sounds good! I\'ll bring the presentation materials...',
        body: `Sounds good! I'll bring the presentation materials and we can review them together.

See you at 2pm.

Bob`,
        date: new Date(Date.now() - 1000 * 60 * 60 * 2),
        read: true,
        starred: false,
        folder: 'inbox',
    },
    {
        id: '3',
        from: 'System Notifications',
        fromEmail: 'noreply@choiros.local',
        to: 'me@choiros.local',
        subject: 'Welcome to ChoirOS Mail',
        preview: 'Welcome to your new mail client! Here\'s how to get started...',
        body: `Welcome to ChoirOS Mail!

Here's how to get started:
- Compose new emails with the button above
- Star important messages
- Archive or delete to keep your inbox clean

Enjoy your new mail experience!

- The ChoirOS Team`,
        date: new Date(Date.now() - 1000 * 60 * 60 * 24),
        read: true,
        starred: false,
        folder: 'inbox',
    },
    {
        id: '4',
        from: 'Carol Davis',
        fromEmail: 'carol@example.com',
        to: 'me@choiros.local',
        subject: 'Design Review Feedback',
        preview: 'Great work on the mockups! I have a few suggestions...',
        body: `Great work on the mockups! I have a few suggestions for the color palette and typography.

Can we schedule a call this week to go over them?

Thanks,
Carol`,
        date: new Date(Date.now() - 1000 * 60 * 60 * 48),
        read: false,
        starred: false,
        folder: 'inbox',
    },
    {
        id: '5',
        from: 'Me',
        fromEmail: 'me@choiros.local',
        to: 'team@example.com',
        subject: 'Weekly Status Report',
        preview: 'Here\'s the summary of this week\'s progress...',
        body: `Hi Team,

Here's the summary of this week's progress:

Completed:
- User authentication module
- Dashboard redesign
- Bug fixes for mobile view

In Progress:
- API optimization
- Documentation updates

Best,
Me`,
        date: new Date(Date.now() - 1000 * 60 * 60 * 72),
        read: true,
        starred: false,
        folder: 'sent',
    },
];

const FOLDERS = [
    { id: 'inbox', label: 'Inbox', icon: Inbox },
    { id: 'starred', label: 'Starred', icon: Star },
    { id: 'sent', label: 'Sent', icon: Send },
    { id: 'archive', label: 'Archive', icon: Archive },
    { id: 'trash', label: 'Trash', icon: Trash2 },
];

function formatDate(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
        return 'Yesterday';
    } else if (days < 7) {
        return date.toLocaleDateString([], { weekday: 'short' });
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
}

export function MailApp() {
    const [emails, setEmails] = useState<Email[]>(SAMPLE_EMAILS);
    const [selectedFolder, setSelectedFolder] = useState('inbox');
    const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [isComposing, setIsComposing] = useState(false);
    const [composeData, setComposeData] = useState({ to: '', subject: '', body: '' });

    const filteredEmails = emails.filter(email => {
        const matchesFolder = selectedFolder === 'starred' 
            ? email.starred 
            : email.folder === selectedFolder;
        const matchesSearch = searchQuery === '' || 
            email.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
            email.from.toLowerCase().includes(searchQuery.toLowerCase()) ||
            email.preview.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesFolder && matchesSearch;
    });

    const unreadCount = emails.filter(e => e.folder === 'inbox' && !e.read).length;

    const handleSelectEmail = (email: Email) => {
        setSelectedEmail(email);
        if (!email.read) {
            setEmails(prev => prev.map(e => 
                e.id === email.id ? { ...e, read: true } : e
            ));
        }
    };

    const handleToggleStar = (emailId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setEmails(prev => prev.map(email => 
            email.id === emailId ? { ...email, starred: !email.starred } : email
        ));
    };

    const handleDelete = (emailId: string) => {
        setEmails(prev => prev.map(email => 
            email.id === emailId ? { ...email, folder: 'trash' as const } : email
        ));
        if (selectedEmail?.id === emailId) {
            setSelectedEmail(null);
        }
    };

    const handleArchive = (emailId: string) => {
        setEmails(prev => prev.map(email => 
            email.id === emailId ? { ...email, folder: 'archive' as const } : email
        ));
        if (selectedEmail?.id === emailId) {
            setSelectedEmail(null);
        }
    };

    const handleSendEmail = () => {
        if (!composeData.to || !composeData.subject) return;
        
        const newEmail: Email = {
            id: Date.now().toString(),
            from: 'Me',
            fromEmail: 'me@choiros.local',
            to: composeData.to,
            subject: composeData.subject,
            preview: composeData.body.slice(0, 100),
            body: composeData.body,
            date: new Date(),
            read: true,
            starred: false,
            folder: 'sent',
        };
        
        setEmails(prev => [newEmail, ...prev]);
        setComposeData({ to: '', subject: '', body: '' });
        setIsComposing(false);
    };

    return (
        <div className="mail-app">
            {/* Sidebar */}
            <div className="mail-sidebar">
                <button 
                    className="mail-compose-btn"
                    onClick={() => setIsComposing(true)}
                >
                    <PenSquare size={16} />
                    Compose
                </button>
                
                <nav className="mail-folders">
                    {FOLDERS.map(folder => {
                        const FolderIcon = folder.icon;
                        const count = folder.id === 'inbox' ? unreadCount : 
                            folder.id === 'starred' ? emails.filter(e => e.starred).length : 0;
                        
                        return (
                            <button
                                key={folder.id}
                                className={`mail-folder ${selectedFolder === folder.id ? 'active' : ''}`}
                                onClick={() => {
                                    setSelectedFolder(folder.id);
                                    setSelectedEmail(null);
                                }}
                            >
                                <FolderIcon size={16} />
                                <span>{folder.label}</span>
                                {count > 0 && <span className="mail-folder-count">{count}</span>}
                            </button>
                        );
                    })}
                </nav>
            </div>

            {/* Email List */}
            <div className="mail-list">
                <div className="mail-list-header">
                    <div className="mail-search">
                        <Search size={14} />
                        <input
                            type="text"
                            placeholder="Search mail..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>
                
                <div className="mail-list-content">
                    {filteredEmails.length === 0 ? (
                        <div className="mail-empty">
                            <Mail size={32} />
                            <p>No emails in {selectedFolder}</p>
                        </div>
                    ) : (
                        filteredEmails.map(email => (
                            <div
                                key={email.id}
                                className={`mail-item ${!email.read ? 'unread' : ''} ${selectedEmail?.id === email.id ? 'selected' : ''}`}
                                onClick={() => handleSelectEmail(email)}
                            >
                                <button 
                                    className={`mail-star ${email.starred ? 'starred' : ''}`}
                                    onClick={(e) => handleToggleStar(email.id, e)}
                                >
                                    <Star size={14} fill={email.starred ? 'currentColor' : 'none'} />
                                </button>
                                <div className="mail-item-content">
                                    <div className="mail-item-header">
                                        <span className="mail-item-from">{email.from}</span>
                                        <span className="mail-item-date">{formatDate(email.date)}</span>
                                    </div>
                                    <div className="mail-item-subject">
                                        {email.hasAttachment && <Paperclip size={12} />}
                                        {email.subject}
                                    </div>
                                    <div className="mail-item-preview">{email.preview}</div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Email Detail / Compose */}
            <div className="mail-detail">
                {isComposing ? (
                    <div className="mail-compose">
                        <div className="mail-compose-header">
                            <h3>New Message</h3>
                            <button onClick={() => setIsComposing(false)}>×</button>
                        </div>
                        <div className="mail-compose-fields">
                            <input
                                type="email"
                                placeholder="To"
                                value={composeData.to}
                                onChange={(e) => setComposeData(prev => ({ ...prev, to: e.target.value }))}
                            />
                            <input
                                type="text"
                                placeholder="Subject"
                                value={composeData.subject}
                                onChange={(e) => setComposeData(prev => ({ ...prev, subject: e.target.value }))}
                            />
                            <textarea
                                placeholder="Write your message..."
                                value={composeData.body}
                                onChange={(e) => setComposeData(prev => ({ ...prev, body: e.target.value }))}
                            />
                        </div>
                        <div className="mail-compose-actions">
                            <button className="mail-send-btn" onClick={handleSendEmail}>
                                <Send size={14} />
                                Send
                            </button>
                        </div>
                    </div>
                ) : selectedEmail ? (
                    <div className="mail-view">
                        <div className="mail-view-header">
                            <h2>{selectedEmail.subject}</h2>
                            <div className="mail-view-actions">
                                <button title="Reply"><Reply size={16} /></button>
                                <button title="Forward"><Forward size={16} /></button>
                                <button title="Archive" onClick={() => handleArchive(selectedEmail.id)}>
                                    <Archive size={16} />
                                </button>
                                <button title="Delete" onClick={() => handleDelete(selectedEmail.id)}>
                                    <Trash2 size={16} />
                                </button>
                                <button title="More"><MoreHorizontal size={16} /></button>
                            </div>
                        </div>
                        <div className="mail-view-meta">
                            <div className="mail-view-avatar">
                                {selectedEmail.from.charAt(0).toUpperCase()}
                            </div>
                            <div className="mail-view-info">
                                <div className="mail-view-from">
                                    <strong>{selectedEmail.from}</strong>
                                    <span>&lt;{selectedEmail.fromEmail}&gt;</span>
                                </div>
                                <div className="mail-view-to">
                                    to {selectedEmail.to}
                                </div>
                            </div>
                            <div className="mail-view-date">
                                {selectedEmail.date.toLocaleString()}
                            </div>
                        </div>
                        <div className="mail-view-body">
                            {selectedEmail.body.split('\n').map((line, i) => (
                                <p key={i}>{line || <br />}</p>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="mail-empty-detail">
                        <Mail size={48} />
                        <p>Select an email to read</p>
                    </div>
                )}
            </div>
        </div>
    );
}
