# Database Migrations Guide

This guide covers database schema migrations for UIT-Go using Alembic.

## 📋 Table of Contents

- [Overview](#overview)
- [Alembic Setup](#alembic-setup)
- [Running Migrations](#running-migrations)
- [Creating Migrations](#creating-migrations)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

### Why Migrations?

Database migrations provide:
- **Version control** for database schema
- **Reproducible** database structure across environments
- **Rollback capability** when issues occur
- **Team collaboration** on schema changes
- **Automated deployment** of database changes

### Services with Migrations

| Service | Database | Migration Tool |
|---------|----------|----------------|
| **UserService** | PostgreSQL | ✅ Alembic |
| **TripService** | CosmosDB (MongoDB) | ❌ Schema-less |
| **DriverService** | CosmosDB (MongoDB) | ❌ Schema-less |
| **LocationService** | Redis | ❌ Key-value store |
| **PaymentService** | CosmosDB (MongoDB) | ❌ Schema-less |

> **Note**: Only UserService uses PostgreSQL and requires schema migrations. MongoDB services are schema-less.

## 🏗️ Alembic Setup

### Directory Structure

```
UserService/
├── alembic.ini                  # Alembic configuration
├── alembic/
│   ├── env.py                   # Environment setup
│   ├── script.py.mako           # Migration template
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_user_role.py
│       └── ...
├── models.py                    # SQLAlchemy models
└── database.py                  # Database connection
```

### Installation

```bash
cd UserService/
pip install alembic
```

### Configuration

The `alembic.ini` file is already configured. Connection string is read from environment variables in `alembic/env.py`.

## 🚀 Running Migrations

### Check Current Version

```bash
cd UserService/
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Upgrade to Latest Version

```bash
# Upgrade to head (latest migration)
alembic upgrade head

# Upgrade by one version
alembic upgrade +1

# Upgrade to specific version
alembic upgrade 001
```

### Downgrade/Rollback

```bash
# Downgrade by one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade 001

# Rollback all migrations
alembic downgrade base
```

## ✍️ Creating Migrations

### Auto-generate Migration

Alembic can auto-generate migrations by comparing your SQLAlchemy models to the current database schema:

```bash
cd UserService/

# Generate migration with descriptive message
alembic revision --autogenerate -m "add_user_role_column"

# This creates a file: alembic/versions/20250115_1234_add_user_role_column.py
```

### Manual Migration

For complex changes, create a manual migration:

```bash
alembic revision -m "add_custom_index"
```

Then edit the generated file:

```python
"""add_custom_index

Revision ID: 002
Revises: 001
Create Date: 2025-01-15 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'

def upgrade() -> None:
    """Add index for better performance"""
    op.create_index(
        'ix_users_created_at',
        'users',
        ['created_at'],
        postgresql_using='btree'
    )

def downgrade() -> None:
    """Remove index"""
    op.drop_index('ix_users_created_at', table_name='users')
```

### Example Migrations

#### Add Column

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='user'))

def downgrade() -> None:
    op.drop_column('users', 'role')
```

#### Modify Column

```python
def upgrade() -> None:
    op.alter_column('users', 'phone_number',
                    existing_type=sa.String(20),
                    type_=sa.String(30),
                    nullable=False)

def downgrade() -> None:
    op.alter_column('users', 'phone_number',
                    existing_type=sa.String(30),
                    type_=sa.String(20),
                    nullable=False)
```

#### Add Foreign Key

```python
def upgrade() -> None:
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

def downgrade() -> None:
    op.drop_table('user_profiles')
```

## 🎯 Best Practices

### 1. Always Test Migrations

```bash
# In development environment
alembic upgrade head    # Test upgrade
alembic downgrade -1    # Test rollback
alembic upgrade head    # Re-apply
```

### 2. Keep Migrations Small

- One logical change per migration
- Easier to review and rollback
- Reduces risk of conflicts

### 3. Write Reversible Migrations

Always implement both `upgrade()` and `downgrade()`:

```python
def upgrade() -> None:
    # Forward migration
    pass

def downgrade() -> None:
    # Rollback migration - must undo upgrade()
    pass
```

### 4. Handle Data Migrations Carefully

When migrating data, use batch operations:

```python
def upgrade() -> None:
    # Add column with default
    op.add_column('users', sa.Column('status', sa.String(20), server_default='active'))

    # Optional: Update existing data
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
```

### 5. Use Transactions

Alembic runs migrations in transactions by default. For complex changes:

```python
def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('new_field', sa.String(50)))
        batch_op.drop_column('old_field')
```

### 6. Document Breaking Changes

```python
"""Remove deprecated email_verified column

⚠️ BREAKING CHANGE: This migration removes the email_verified column.
Applications must update to use the new email_status column instead.

Revision ID: 003
Revises: 002
"""
```

## 🚀 Deployment Workflow

### Local Development

```bash
# 1. Create migration
alembic revision --autogenerate -m "your_change"

# 2. Review generated file
cat alembic/versions/latest_migration.py

# 3. Test migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 4. Commit migration file
git add alembic/versions/
git commit -m "Add migration: your_change"
```

### Production Deployment

```bash
# Run migrations before deploying new code
alembic upgrade head

# Deploy new application code
kubectl apply -f k8s/userservice.yaml
```

### CI/CD Integration

Add to `.github/workflows/deploy.yml`:

```yaml
- name: Run database migrations
  run: |
    cd UserService/
    alembic upgrade head
```

## 🐛 Troubleshooting

### Migration Fails

```bash
# Check current state
alembic current

# View pending migrations
alembic heads

# Mark migration as applied without running it (use cautiously)
alembic stamp head
```

### Conflicts After Merge

If multiple developers create migrations:

```bash
# Check for multiple heads
alembic heads

# Merge heads
alembic merge -m "merge_branches" head1 head2
```

### Reset Migration History

**⚠️ DANGEROUS - Only for development!**

```bash
# Drop all tables
# Re-initialize Alembic
alembic stamp base
alembic upgrade head
```

### Database Out of Sync

```bash
# Generate migration to sync database
alembic revision --autogenerate -m "sync_database"

# Review and apply
alembic upgrade head
```

## 📊 Migration Status

### Current Migrations

```bash
# List all migrations
alembic history

# Check which migrations are applied
alembic current -v

# Show SQL without executing
alembic upgrade head --sql
```

## 🔍 Advanced Usage

### Offline SQL Generation

Generate SQL for DBA review:

```bash
alembic upgrade head --sql > migration.sql
```

### Branching and Merging

```bash
# Create branch
alembic revision -m "feature_branch" --branch-label feature

# Merge branches
alembic merge -m "merge_feature" head1 head2
```

### Custom Script Template

Edit `alembic/script.py.mako` to customize migration templates.

## 📚 Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)

## 🎯 Next Steps

1. ✅ Alembic configured for UserService
2. ⏳ Create migration for user roles/permissions
3. ⏳ Setup automated migration testing in CI/CD
4. ⏳ Document rollback procedures for production
5. ⏳ Setup migration monitoring/alerts
