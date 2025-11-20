"""PostgreSQL client for state, task, and conversation storage."""
import logging
import json
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values, Json
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extensions import register_adapter
from psycopg2 import sql
from config import Config
from shared.storage_client import StorageClient
from shared.conversation_store import ConversationStore

logger = logging.getLogger(__name__)

# Register JSON adapter for psycopg2
register_adapter(dict, Json)


class PostgreSQLClient(StorageClient):
    """PostgreSQL client for storing agent states, tasks, and conversations."""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or Config.POSTGRES_CONNECTION_STRING
        
        if not self.connection_string:
            raise ValueError("POSTGRES_CONNECTION_STRING is required")
        
        # Create connection pool
        try:
            self.pool = ThreadedConnectionPool(1, 5, self.connection_string)
            self._initialize_database()
            logger.info("PostgreSQL client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL: {str(e)}")
            raise
    
    def _get_connection(self):
        """Get connection from pool."""
        return self.pool.getconn()
    
    def _return_connection(self, conn):
        """Return connection to pool."""
        self.pool.putconn(conn)
    
    def _initialize_database(self):
        """Initialize database tables."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Create tables if they don't exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agent_states (
                        id VARCHAR(255) PRIMARY KEY,
                        agent_id VARCHAR(255) NOT NULL,
                        state_id VARCHAR(255) NOT NULL,
                        state JSONB NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(agent_id, state_id)
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agent_tasks (
                        id VARCHAR(255) PRIMARY KEY,
                        agent_id VARCHAR(255) NOT NULL,
                        task_id VARCHAR(255) NOT NULL,
                        task_data JSONB NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(agent_id, task_id)
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(255) PRIMARY KEY,
                        conversation_id VARCHAR(255) NOT NULL,
                        message JSONB NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id VARCHAR(255) PRIMARY KEY,
                        case_id VARCHAR(255) NOT NULL,
                        transaction JSONB NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create indexes for better query performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_agent_states_agent_state 
                    ON agent_states(agent_id, state_id);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent_task 
                    ON agent_tasks(agent_id, task_id);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_conv_id 
                    ON conversations(conversation_id);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_case_id 
                    ON transactions(case_id);
                """)
                
                conn.commit()
                logger.info("PostgreSQL tables initialized")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error initializing PostgreSQL tables: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def save_state(self, agent_id: str, state_id: str, state: Dict[str, Any]):
        """Save agent state to PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                doc_id = f"{agent_id}_{state_id}"
                timestamp = state.get("timestamp", "")
                
                cur.execute("""
                    INSERT INTO agent_states (id, agent_id, state_id, state, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        state = EXCLUDED.state,
                        timestamp = EXCLUDED.timestamp
                """, (doc_id, agent_id, state_id, Json(state), timestamp))
                
                conn.commit()
                logger.info(f"Saved state for {agent_id}: {state_id}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving state: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def get_state(self, agent_id: str, state_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent state from PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                doc_id = f"{agent_id}_{state_id}"
                
                cur.execute("""
                    SELECT state FROM agent_states 
                    WHERE id = %s
                """, (doc_id,))
                
                row = cur.fetchone()
                if row:
                    # JSONB is returned as dict by psycopg2 with Json adapter
                    return row['state']
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving state: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def save_task(self, agent_id: str, task_id: str, task_data: Dict[str, Any]):
        """Save task details to PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                doc_id = f"{agent_id}_{task_id}"
                timestamp = task_data.get("timestamp", "")
                
                cur.execute("""
                    INSERT INTO agent_tasks (id, agent_id, task_id, task_data, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        task_data = EXCLUDED.task_data,
                        timestamp = EXCLUDED.timestamp
                """, (doc_id, agent_id, task_id, Json(task_data), timestamp))
                
                conn.commit()
                logger.info(f"Saved task for {agent_id}: {task_id}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving task: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def get_task(self, agent_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task details from PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                doc_id = f"{agent_id}_{task_id}"
                
                cur.execute("""
                    SELECT task_data FROM agent_tasks 
                    WHERE id = %s
                """, (doc_id,))
                
                row = cur.fetchone()
                if row:
                    # JSONB is returned as dict by psycopg2 with Json adapter
                    return row['task_data']
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving task: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def save_conversation(self, conversation_id: str, message: Dict[str, Any]):
        """Save conversation message to PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                message_id = message.get("id", f"{conversation_id}_{message.get('timestamp', '')}")
                timestamp = message.get("timestamp", "")
                
                cur.execute("""
                    INSERT INTO conversations (id, conversation_id, message, timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        message = EXCLUDED.message,
                        timestamp = EXCLUDED.timestamp
                """, (message_id, conversation_id, Json(message), timestamp))
                
                conn.commit()
                logger.debug(f"Saved conversation message: {conversation_id}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving conversation: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history from PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT message FROM conversations 
                    WHERE conversation_id = %s 
                    ORDER BY timestamp ASC
                """, (conversation_id,))
                
                rows = cur.fetchall()
                # JSONB is returned as dict by psycopg2 with Json adapter
                return [row['message'] for row in rows]
                
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []
        finally:
            self._return_connection(conn)
    
    def save_transactions(self, case_id: str, transactions: List[Dict[str, Any]]):
        """Save transactions to PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Prepare data for bulk insert
                values = []
                for transaction in transactions:
                    transaction_id = transaction.get("transaction_id", f"{case_id}_{transaction.get('id', '')}")
                    timestamp = transaction.get("timestamp", "")
                    values.append((
                        transaction_id,
                        case_id,
                        Json(transaction),
                        timestamp
                    ))
                
                execute_values(
                    cur,
                    """
                    INSERT INTO transactions (id, case_id, transaction, timestamp)
                    VALUES %s
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        transaction = EXCLUDED.transaction,
                        timestamp = EXCLUDED.timestamp
                    """,
                    values
                )
                
                conn.commit()
                logger.info(f"Saved {len(transactions)} transactions for case: {case_id}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving transactions: {str(e)}")
            raise
        finally:
            self._return_connection(conn)
    
    def get_transactions(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve transactions for a case from PostgreSQL."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT transaction FROM transactions 
                    WHERE case_id = %s 
                    ORDER BY timestamp ASC
                """, (case_id,))
                
                rows = cur.fetchall()
                # JSONB is returned as dict by psycopg2 with Json adapter
                return [row['transaction'] for row in rows]
                
        except Exception as e:
            logger.error(f"Error retrieving transactions: {str(e)}")
            return []
        finally:
            self._return_connection(conn)
    
    def close(self):
        """Close connection pool."""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")


class PostgreSQLConversationStore(ConversationStore):
    def __init__(self):
        self.conn = psycopg2.connect(Config.POSTGRES_CONNECTION_STRING)
        self._ensure_table()

    def _ensure_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    message JSONB NOT NULL
                )
            """)
            self.conn.commit()

    def save_conversation(self, context_id: str, user: str, message: Dict[str, Any]):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (id, context_id, user, message) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), context_id, user, psycopg2.extras.Json(message))
            )
            self.conn.commit()
        logger.info(f"Saved message for context {context_id}, user {user} in PostgreSQL")

    def get_conversation(self, context_id: str, user: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if user:
                cur.execute("SELECT message FROM conversations WHERE context_id=%s AND user=%s", (context_id, user))
            else:
                cur.execute("SELECT message FROM conversations WHERE context_id=%s", (context_id,))
            rows = cur.fetchall()
        logger.info(f"Retrieved {len(rows)} messages for context {context_id}, user {user} from PostgreSQL")
        return [row["message"] for row in rows]

    def summarize_conversation(self, context_id: str, user: Optional[str] = None) -> str:
        messages = self.get_conversation(context_id, user)
        summary = f"Summary for context {context_id}, user {user}: {len(messages)} messages."
        # Optionally, use LLM or custom logic for richer summary
        logger.info(f"Summarized conversation for context {context_id}, user {user}")
        return summary

