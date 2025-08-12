"""updated_at_fix

Revision ID: c954bd745120
Revises: 1e0e67ae54f0
Create Date: 2025-08-12 19:44:37.190229

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c954bd745120'
down_revision = '1e0e67ae54f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create a function to update the updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create triggers for tables with updated_at columns

    # Trigger for users table
    op.execute("""
        CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON users 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # Trigger for user_subscriptions table
    op.execute("""
        CREATE TRIGGER update_user_subscriptions_updated_at 
        BEFORE UPDATE ON user_subscriptions 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.execute("DROP TRIGGER IF EXISTS update_user_subscriptions_updated_at ON user_subscriptions;")

    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
