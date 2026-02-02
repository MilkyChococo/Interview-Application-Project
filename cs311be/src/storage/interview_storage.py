from datetime import datetime
from typing import Any, Dict, List, Optional

from src.storage.mongodb import CRUDDocuments


class CRUDInterviewSession(CRUDDocuments):
    def __init__(self):
        super().__init__()
        self.collection = CRUDDocuments.connection.db.interview_sessions


class InterviewStorage:
    def __init__(self):
        self.collection = CRUDInterviewSession()

    def create_session(
        self,
        session_id: str,
        user_id: str = "",
        source: str = "",
        keywords: List[str] = [],
        questions: List[Dict[str, Any]] = [],
        job_description: str = "",
        user_project: str = "",
        plan: str = "",
    ) -> str:
        doc = {
            "session_id": session_id,
            "user_id": user_id,
            "source": source,
            "keywords": keywords,
            "questions": questions,  # [{"text": str, "metadata": {...}}]
            "interactions": [],  # [{"question": str, "answer": str, "evaluation": str}]
            "current_index": 0,
            "status": "in_progress",
            "job_description": job_description,
            "user_project": user_project,
            "plan": plan,
            "content_type": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return self.collection.insert_one_doc(doc)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        # For backward compatibility, search without user_id filter
        return self.collection.find_one_doc({"session_id": session_id})

    def update_session(self, session_id: str, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one_doc({"session_id": session_id}, {"$set": updates})
    def update_user_id(self, session_id: str, user_id: str):
        self.collection.update_one_doc({"session_id": session_id}, {"$set": {"user_id": user_id}})
    def append_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        evaluation: str,
        contexts: Optional[List[str]] = None,
        ground_truth: str = "",
        question_original: str = "",
    ):
        update = {
            "$push": {
                "interactions": {
                    "question": question,
                    "answer": answer,
                    "evaluation": evaluation,
                    "contexts": contexts or [],
                    "ground_truth": ground_truth,
                    "question_original": question_original,
                }
            },
            "$set": {"updated_at": datetime.utcnow()},
        }
        self.collection.update_one_doc({"session_id": session_id}, update)
    def find_sessions_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Find all sessions for a specific user"""
        return self.collection.read_documents({"user_id": user_id})
    
    def find(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic find method for custom queries"""
        return self.collection.read_documents(query)
    
    def find_completed_sessions_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Find all completed sessions for a specific user"""
        return self.collection.read_documents({"user_id": user_id, "status": "completed"})
    
    def find_active_sessions_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Find all active sessions for a specific user"""
        return self.collection.read_documents({"user_id": user_id, "status": "in_progress"})
    
    def get_session_count_by_user_id(self, user_id: str) -> int:
        """Get total number of sessions for a user"""
        return len(self.collection.read_documents({"user_id": user_id}))
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session by session_id"""
        try:
            self.collection.delete_one_doc({"session_id": session_id})
            return True
        except Exception:
            return False

