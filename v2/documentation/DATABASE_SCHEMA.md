# Initial database schema

The first migration creates users with Google subject, unique email, approval status and Super Admin flag; roles and permissions with many-to-many mappings; teams and membership; hashed opaque session tokens with expiry and revocation; and audit log records.

Lead, discovery, AI and agent tables will be introduced through additive migrations in their respective milestones.
