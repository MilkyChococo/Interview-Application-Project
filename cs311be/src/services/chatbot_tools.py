import os
from typing import List, Tuple, Dict, Any
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core import Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexAutoRetriever, VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.tools import FunctionTool
from llama_index.core.schema import NodeWithScore, TextNode
import chromadb
from src.engines.llm_engine import LLMEngine
from src.prompts.prompt import *
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
import re
from src.storage.interview_storage import InterviewStorage
import json

from dotenv import load_dotenv
load_dotenv()

TOP_K = int(os.getenv("TOP_K", "5"))  # Default to 5 if not set
K_CANDIDATES = int(os.getenv("RAG_K_CANDIDATES", "20"))
K_RERANK = int(os.getenv("RAG_K_RERANK", "5"))

# Get vectorstore path from environment or use default
vectorstore_path = "D:\CODE\DSC\dsc2025API\src\chroma_db_master_program"
print(f"Path exists: {os.path.exists(vectorstore_path)}")
# Check if the environment path exists, if not use local path
if vectorstore_path and os.path.exists(vectorstore_path):
    pass  # Use environment path
else:
    # Force use local chroma_db_master_program directory
    vectorstore_path = "./src/chroma_db_master_program"

vectorstore_path = os.path.abspath(vectorstore_path)
# vectorstore_path = "../../chroma_db_eachfileisanode"


class ChatbotTools:
    def __init__(self):

        """
        Tools for chatbot agent.
        """

        # Initialize LLM and embedding model
        self.engine = LLMEngine()
        self.llm = self.engine.openai_llm
        self.embed_model = self.engine.embed_model
        Settings.embed_model = self.embed_model
        Settings.llm = self.llm

        # Initialize vector stores and retrievers
        self.qa_retriever = self._initialize_qa_retriever()
        # self.evaluation = self._evaluation_question()
        self.interview_storage = InterviewStorage()

    @staticmethod
    def _extract_node_text(node: Any) -> str:
        text = getattr(node, "text", None)
        if not text and hasattr(node, "node"):
            inner = getattr(node, "node", None)
            text = getattr(inner, "text", None) if inner is not None else None
        return text or ""

    @staticmethod
    def _extract_node_metadata(node: Any) -> Dict[str, Any]:
        if hasattr(node, "node"):
            inner = getattr(node, "node", None)
            if inner is not None and hasattr(inner, "metadata"):
                return dict(getattr(inner, "metadata", {}) or {})
        return dict(getattr(node, "metadata", {}) or {})

    @staticmethod
    def _extract_reference_answer(text: str, metadata: Dict[str, Any]) -> str:
        reference = metadata.get("answer") if metadata else None
        if reference:
            return reference
        if text:
            match = re.search(r"Answer\s*:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""
    def _initialize_qa_retriever(self, top_k: int = TOP_K):
        db = chromadb.PersistentClient(path=vectorstore_path)
        chroma_collection = db.get_or_create_collection("question_collection")
        total_count = chroma_collection.count()
        print(f"Total questions in 'question_collection': {total_count}")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        return VectorIndexRetriever(index=index, similarity_top_k=top_k)
    

    def re_write_question(self, node, user_project: str):
        """Refine/clarify a question to better match user's background and ensure actionable, scenario-based phrasing.

        Args:
            node: question node (may be NodeWithScore or a node-like object with .text)
            user_project: user's background/experience text to tailor the question

        Returns:
            The same node object with an improved .text field when possible; otherwise returns node unchanged.
        """
        try:
            # Extract original text from node in a defensive way
            original_text = self._extract_node_text(node)

            # Fallbacks
            if not original_text:
                return node

            prompt = f"""
You are a technical interview expert. Please refine the following question to:
- Be clear, focus on scenarios/practical situations rather than asking for definitions
- Match the candidate's experience
- Keep the original topic, don't expand too much
- Be concise, one sentence, in English
Candidate's experience:
{user_project}
Original question:
{original_text}
Refined question:
""".strip()

            result = self.llm.complete(prompt=prompt)
            improved = result.text.strip() if getattr(result, "text", None) else str(result).strip()
            if not improved:
                return node

            # Build a new node instead of mutating (NodeWithScore.text is read-only)
            try:
                base = getattr(node, "node", None)
                score = getattr(node, "score", None)
                metadata = self._extract_node_metadata(node)
                metadata["refined"] = True
                metadata.setdefault("original_text", original_text)
                new_text_node = TextNode(text=improved, metadata=metadata)
                new_node = NodeWithScore(node=new_text_node, score=score)
            except Exception as inner_e:
                from types import SimpleNamespace
                new_node = SimpleNamespace(text=improved, metadata=dict(getattr(node, "metadata", {}) or {}))
            print(f"Refined question: {getattr(new_node, 'text', '')}")
            return new_node
        except Exception as e:
            # In case of any failure, return original node
            print(f"Error refining question: {e}")
            return node

    async def _llm_rerank_nodes(
        self,
        nodes: List[NodeWithScore],
        user_project: str,
        job_description: str,
        top_k: int = K_RERANK,
    ) -> List[NodeWithScore]:
        """
        Rerank candidate questions with LLM and return top_k nodes.
        """
        if not nodes:
            return []
        if len(nodes) <= top_k:
            return nodes

        questions_list = []
        for i, node in enumerate(nodes):
            question_text = self._extract_node_text(node)
            if question_text:
                questions_list.append(f"{i}: {question_text}")

        prompt = f"""
You are a technical interviewer. Select the top {top_k} most relevant questions
for the candidate based on their CV and job description.

Candidate CV/Experience:
{user_project}

Job Description:
{job_description}

Candidate Questions:
{chr(10).join(questions_list)}

Rules:
- Prefer practical, scenario-based questions.
- Avoid basic definition questions if possible.
- Return ONLY a comma-separated list of indexes (e.g., "0,2,5,7,9").
""".strip()

        try:
            response = await self.llm.acomplete(prompt=prompt)
            raw = (response.text or "").strip()
            picks = []
            for part in raw.replace(" ", "").split(","):
                if part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(nodes):
                        picks.append(idx)
            # De-duplicate while preserving order
            seen = set()
            picks = [i for i in picks if not (i in seen or seen.add(i))]
            if picks:
                return [nodes[i] for i in picks[:top_k]]
        except Exception as e:
            print(f"Error in LLM rerank: {e}")

        # Fallback: use vector similarity scores
        ranked = sorted(nodes, key=lambda n: (n.score or 0), reverse=True)
        return ranked[:top_k]

    async def _rewrite_question_with_context(
        self,
        question: str,
        user_project: str,
        job_description: str,
    ) -> str:
        """
        Rewrite a question to be concise and tailored to CV + JD context.
        """
        if not question:
            return question
        prompt = f"""
You are a technical interview expert. Rewrite the question to:
- Be clear and scenario/practical oriented
- Match the candidate's experience and the job requirements
- Keep the original topic, do not expand scope
- Be concise, one sentence, in English

Candidate's experience:
{user_project}

Job description:
{job_description}

Original question:
{question}

Rewritten question:
""".strip()
        result = await self.llm.acomplete(prompt=prompt)
        rewritten = result.text.strip() if getattr(result, "text", None) else str(result).strip()
        return rewritten or question

    async def _rewrite_nodes_with_context(
        self,
        nodes: List[NodeWithScore],
        user_project: str,
        job_description: str,
    ) -> List[NodeWithScore]:
        if not nodes:
            return []
        rewritten_nodes: List[NodeWithScore] = []
        for node in nodes:
            original_text = self._extract_node_text(node)
            rewritten = await self._rewrite_question_with_context(original_text, user_project, job_description)
            try:
                base = getattr(node, "node", None)
                score = getattr(node, "score", None)
                metadata = self._extract_node_metadata(node)
                metadata["refined"] = True
                metadata.setdefault("original_text", original_text)
                new_text_node = TextNode(text=rewritten, metadata=metadata)
                new_node = NodeWithScore(node=new_text_node, score=score)
            except Exception:
                from types import SimpleNamespace
                new_node = SimpleNamespace(text=rewritten, metadata=dict(getattr(node, "metadata", {}) or {}))
            rewritten_nodes.append(new_node)
        return rewritten_nodes


    async def qa_information(self, query: str) -> str:
        nodes = await self.qa_retriever.aretrieve(query)
        if not nodes:
            return "No relevant information found in the QA."
        return "\n\n---\n\n".join(
            f"Domain: {node.metadata['source']} Question ID: {node.metadata['index']} Question content: {node.text}" for node in nodes
        )
    async def evaluate_user_answer(self, question: str, user_answer: str, source: str) -> str:
        """
        Evaluate the user's answer based on the reference answer in the question's metadata.

        Args:
            question: The interview question to evaluate.
            user_answer: The candidate's answer.

        Returns:
            Structured feedback text including: score (0-10), brief feedback, and 3 improvement suggestions.
        """
        # Lấy các node liên quan nhất từ cả hai bộ sưu tập
        # db = chromadb.PersistentClient(path=vectorstore_path)
        # chroma_collection = db.get_or_create_collection("software")
        # reference_answer = chroma_collection.get(ids=[f"Software_QA-{index}"]).get("metadatas")
        # reference_answer = reference_answer[0].get("answer")
        # for i in range(len(reference_answer)):
        #     print(i, reference_answer[i])
        # print(reference_answer)
        all_nodes: List[NodeWithScore] = []
        qa_nodes = await self.qa_retriever.aretrieve(question)
        all_nodes.extend(qa_nodes)
    
        if not all_nodes:
            return "No matching question found to compare answers. Please provide a clear question."

        # Chọn node có điểm tương đồng cao nhất
        best_node = max(all_nodes, key=lambda n: (n.score or 0))

        # Lấy đáp án mẫu từ metadata, nếu không có thì thử tách từ text theo mẫu "Answer:"
        reference_answer = None
        try:
            reference_answer = best_node.metadata.get("answer")
        except Exception:
            reference_answer = None

        if not reference_answer and best_node.text:
            match = re.search(r"Answer\s*:\s*(.*)", best_node.text, re.IGNORECASE | re.DOTALL)
            if match:
                reference_answer = match.group(1).strip()

        if not reference_answer:
            return "No reference answer found in the data for this question to evaluate."

        eval_prompt = f"""
You are an interview expert. Please score and provide feedback on the candidate's answer.
Question: {question}
Reference answer (ground-truth): {reference_answer}
Candidate's answer: {user_answer}
Requirements:
- Score on a scale of 0-10 (single integer value only).
- Refer to the reference answer and professional knowledge to score. Candidates may answer differently from the reference but still be correct and receive a high score.
- Evaluate based on criteria: Relevance, Difficulty level, Clarity, etc.
- Provide specific, actionable improvement suggestions.
Output format:
Score: <number from 0 to 10> (Only one integer value, no commas, do not display /10)
Feedback: <short paragraph> (Do not comment on the reference answer. For example, do not say "the candidate's answer is similar to the reference answer")
Strengths:
- <strength 1>
- <strength 2>
Improvements:
- <suggestion 1>
- <suggestion 2>
- <suggestion 3>
Example:
Score: 8
Feedback: The answer is accurate, complete, clear, and relevant to the question. However, it could be improved by adding more examples and details.
Strengths:
- Good understanding of the core concepts
- Clear communication style
Improvements:
- Practice more exercises related to the concepts and algorithms
- Learn more about real-world applications of the concepts and algorithms
"""
        result = self.llm.complete(prompt=eval_prompt)
        return result.text.strip() if getattr(result, "text", None) else str(result) 


    async def _generate_keywords(self, plan: str, user_project: str, job_description: str, number: str) -> List[str]:
        prompt = f"""
            Bạn là chuyên gia tuyển dụng chuyên sâu về lĩnh vực AI và công nghệ. Dựa trên kế hoạch phỏng vấn, kinh nghiệm ứng viên, và yêu cầu công việc, hãy tạo danh sách {number} từ khóa để truy vấn câu hỏi phỏng vấn từ VectorDB.
            Kế hoạch phỏng vấn: {plan}
            Kinh nghiệm ứng viên: {user_project}
            Yêu cầu công việc: {job_description}
            Yêu cầu:
            - Chỉ tạo đúng {number} từ khóa, không nhiều hơn hoặc ít hơn.
            - Mỗi từ khóa phải tập trung vào một chủ đề, kỹ thuật, thuật toán, framework, hoặc kỹ năng cụ thể (bao gồm cả soft skills), kết hợp với kinh nghiệm của ứng viên và yêu cầu công việc.
            - Mỗi từ khóa phải bao gồm khía cạnh như vai trò, hoạt động, định nghĩa, cách triển khai, hoặc ứng dụng thực tế, nhưng không được quá rộng hoặc chung chung.
            - Từ khóa phải ngắn gọn, dài khoảng 2 đến 5 từ (words), mô tả rõ ràng và ý nghĩa để tối ưu hóa việc retrieve câu hỏi liên quan.
            - Các từ khóa phải đảm bảo được ý nghĩa trong việc tìm câu hỏi.
            - Chỉ trả về danh sách từ khóa, phân tách bằng dấu phẩy, không có số thứ tự, không có giải thích thêm.
            Ví dụ:
                Plan: "Chủ đề 1: Machine Learning (3 câu hỏi), Chủ đề 2: Deep Learning (2 câu hỏi)"
                Kinh nghiệm ứng viên: "Xây dựng mô hình phân loại hình ảnh sử dụng CNN, triển khai pipeline xử lý dữ liệu lớn với Python và TensorFlow."
                Yêu cầu công việc: "Kỹ năng thành thạo TensorFlow, kinh nghiệm triển khai mô hình deep learning trên cloud."
                number: 5
                Kết quả: CNN phân loại, gradient descent, dữ liệu lớn, cloud deployment, transfer learning

                Plan: "Chủ đề 1: Algorithms (2 câu hỏi), Chủ đề 2: Data Structures (3 câu hỏi)"
                Kinh nghiệm ứng viên: "Phát triển hệ thống tìm kiếm với binary search tree, tối ưu hóa thuật toán tìm đường ngắn nhất bằng Dijkstra."
                Yêu cầu công việc: "Hiểu biết sâu về thuật toán tìm kiếm và cấu trúc dữ liệu, tối ưu hóa hiệu suất."
                number: 5
                Kết quả: binary search, thuật toán Dijkstra, hash table, tối ưu hiệu suất, priority queue

                Plan: "Chủ đề 1: Natural Language Processing (2 câu hỏi), Chủ đề 2: Python Frameworks (3 câu hỏi)"
                Kinh nghiệm ứng viên: "Xây dựng chatbot với BERT và Flask, triển khai API xử lý văn bản với FastAPI."
                Yêu cầu công việc: "Thành thạo FastAPI, kinh nghiệm xây dựng hệ thống NLP thời gian thực."
                number: 5
                Kết quả: BERT xử lý, API FastAPI, chatbot Flask, fine-tuning BERT, NLP thời gian thực

                Plan: "Chủ đề 1: Soft Skills (3 câu hỏi), Chủ đề 2: Team Collaboration (2 câu hỏi)"
                Kinh nghiệm ứng viên: "Dẫn dắt nhóm phát triển AI trong dự án chatbot, phối hợp với đội ngũ DevOps để triển khai hệ thống."
                Yêu cầu công việc: "Kỹ năng lãnh đạo, khả năng làm việc nhóm và quản lý dự án hiệu quả."
                number: 5
                Kết quả: giao tiếp nhóm, giải quyết xung đột, tinh thần đồng đội, quản lý dự án, phối hợp DevOps
            """

        result = self.llm.complete(prompt=prompt)
        text = result.text if getattr(result, "text", None) else str(result)
        keywords = [kw.strip() for kw in text.replace("\n", ",").split(",") if kw.strip()]
        # Deduplicate while preserving order
        seen = set()
        deduped: List[str] = []
        for kw in keywords:
            low = kw.lower()
            if low not in seen:
                seen.add(low)
                deduped.append(kw)
        return deduped

    def _get_retriever_by_source(self, top_k: int = TOP_K) -> VectorIndexRetriever:
        self.qa_retriever = self._initialize_qa_retriever(top_k=top_k)
        return self.qa_retriever
    async def re_rank_nodes(self, nodes: List[NodeWithScore], user_project: str, job_description: str, collected: Dict[str, Dict[str, Any]]) -> NodeWithScore:
        """
        Chọn câu hỏi phù hợp nhất với CV của ứng viên và yêu cầu công việc từ danh sách các nodes.
        
        Args:
            nodes: Danh sách các nodes chứa câu hỏi phỏng vấn
            user_project: Kỹ năng và kinh nghiệm của ứng viên từ CV
            job_description: Mô tả công việc và yêu cầu của vị trí
            collected: Danh sách các câu hỏi đã chọn
        Returns:
            NodeWithScore: Node chứa câu hỏi phù hợp nhất với CV và JD
        """
        if not nodes:
            return None
            
        if len(nodes) == 1:
            return nodes[0]
        
        # Tạo danh sách câu hỏi để LLM dễ đọc
        questions_list = []
        for i, node in enumerate(nodes):
            question_text = self._extract_node_text(node)
            questions_list.append(f"{i}: {question_text}")
        collected_text = ""
        questions_text = "\n".join(questions_list)
        for key, value in collected.items():
            collected_text += f"\n{key}: {value['text']}"
        prompt = f"""
        Bạn là chuyên gia tuyển dụng có kinh nghiệm. Nhiệm vụ của bạn là chọn câu hỏi phỏng vấn phù hợp nhất với kinh nghiệm của ứng viên và yêu cầu của vị trí công việc.

        THÔNG TIN ỨNG VIÊN:
        {user_project}

        MÔ TẢ CÔNG VIỆC:
        {job_description}

        DANH SÁCH CÂU HỎI PHỎNG VẤN:
        {questions_text}
        
        YÊU CẦU:
        - Phân tích kinh nghiệm ứng viên, yêu cầu công việc và các câu hỏi phỏng vấn
        - Hạn chế các câu hỏi về định nghĩa và khái niệm cơ bản như "OOP là gì?"
        - Ưu tiên câu hỏi liên quan trực tiếp đến kỹ năng mà ứng viên có VÀ yêu cầu của công việc
        - Chọn câu hỏi đánh giá khả năng thực tế và kinh nghiệm làm việc
        - Ưu tiên câu hỏi về implementation, best practices, và problem-solving
        - Không chọn các câu giống hoặc tương tự với các câu đã chọn trong dánh sách sau:
        {collected_text}
        ĐỊNH DẠNG TRẢ VỀ:
        Chỉ trả về số thứ tự của câu hỏi phù hợp nhất (0, 1, 2, ...).

        VÍ DỤ:
        Nếu câu hỏi phù hợp nhất là câu số 2, trả về: 2
        """
        
        try:
            response = await self.llm.acomplete(prompt=prompt)
            selected_index = int(response.text.strip())
            
            # Kiểm tra index hợp lệ
            if 0 <= selected_index < len(nodes):
                # Refine the selected question before returning
                return self.re_write_question(nodes[selected_index], user_project)
                
            else:
                # Nếu index không hợp lệ, trả về node đầu tiên (sau khi refine)
                return self.re_write_question(nodes[0], user_project)
                
        except (ValueError, IndexError) as e:
            print(f"Error parsing LLM response: {e}, returning first node")
            return self.re_write_question(nodes[0], user_project)
        except Exception as e:
            print(f"Error in re_rank_nodes: {e}, returning first node")
            return self.re_write_question(nodes[0], user_project)


    async def start_interview(self, plan: str, source: str, session_id: str, user_project: str, job_description: str, number: str, user_id: str = "") -> Dict[str, Any]:
        try:
            target_n = max(1, int(str(number).strip()))
        except Exception:
            target_n = max(1, int(TOP_K))

        keywords = await self._generate_keywords(plan, user_project, job_description, str(target_n))
        if len(keywords) > target_n:
            keywords = keywords[:target_n]
        retriever = self._get_retriever_by_source(top_k=K_CANDIDATES)
        collected: Dict[str, Dict[str, Any]] = {}
        print(f"Generated {len(keywords)} keywords: {keywords}")
        for i, kw in enumerate(keywords):
            try:
                result = await retriever.aretrieve(kw)
                # vector search candidates
                nodes = result if isinstance(result, list) else [result] if result else []
                contexts = [self._extract_node_text(n) for n in nodes if self._extract_node_text(n)]
                if nodes:
                    # LLM rerank to top K
                    ranked_nodes = await self._llm_rerank_nodes(nodes, user_project, job_description, top_k=K_RERANK)
                    # Only rewrite 1 best question per keyword
                    best_node = ranked_nodes[0] if ranked_nodes else None
                    if best_node:
                        nodes = await self._rewrite_nodes_with_context([best_node], user_project, job_description)
                    else:
                        nodes = []
                else:
                    nodes = []
            except Exception as e:
                print(f"Error retrieving for keyword '{kw}': {e}")
                nodes = []
                contexts = []
                
            for node in nodes:
                if not node:
                    continue
                # Defensive checks in case of unexpected shapes
                node_text = self._extract_node_text(node)
                if not node_text:
                    continue
                text_key = node_text.strip()
                if not text_key:
                    continue
                if text_key in collected:
                    # allow duplicates if needed to reach target_n
                    suffix = 2
                    new_key = f"{text_key} ({suffix})"
                    while new_key in collected:
                        suffix += 1
                        new_key = f"{text_key} ({suffix})"
                    text_key = new_key
                metadata = self._extract_node_metadata(node)
                original_text = metadata.get("original_text") or node_text
                ground_truth = self._extract_reference_answer(original_text, metadata)
                collected[text_key] = {
                    "text": node_text,
                    "metadata": metadata,
                    "contexts": contexts,
                    "ground_truth": ground_truth,
                    "original_text": original_text,
                    "keyword": kw,
                }
                if len(collected) >= target_n:
                    break
            if len(collected) >= target_n:
                break

        questions = list(collected.values())
        if not questions:
            return {"message": "Không tìm thấy câu hỏi phù hợp.", "keywords": keywords, "questions": questions}

        self.interview_storage.create_session(
            session_id=session_id,
            user_id=user_id,
            source=source,
            keywords=keywords,
            questions=questions,
            job_description=job_description,
            user_project=user_project,
            plan=plan,
        )

        return {
            "session_id": session_id,
            "source": source,
            "keywords": keywords,
            "total_questions": len(questions),
            "next_index": 0,
            "next_question": questions[0],
        }

    async def submit_interview_answer(self, session_id: str, user_answer: str, source: str) -> Dict[str, Any]:
        session = self.interview_storage.get_session(session_id)
        if not session:
            return {"error": "Không tìm thấy phiên phỏng vấn"}
        idx = int(session.get("current_index"))
        print(idx)
        questions: List[Dict[str, Any]] = session.get("questions", [])
        if idx >= len(questions):
            return {"message": "Đã hết câu hỏi", "done": True}
        qobj = questions[idx]
        question_text: str = qobj.get("text", "")
        contexts = qobj.get("contexts", []) or []
        ground_truth = qobj.get("ground_truth", "")
        if not ground_truth:
            metadata = qobj.get("metadata", {}) or {}
            original_text = qobj.get("original_text") or question_text
            ground_truth = self._extract_reference_answer(original_text, metadata)
        # Use the source parameter passed in, fallback to session source if needed
        session_source = session.get("source", "Software_QA")
        source_to_use = source if source else session_source

        evaluation = await self.evaluate_user_answer(question_text, user_answer, source_to_use)

        self.interview_storage.append_interaction(
            session_id=session_id,
            question=question_text,
            answer=user_answer,
            evaluation=evaluation,
            contexts=contexts,
            ground_truth=ground_truth,
            question_original=qobj.get("original_text", ""),
        )
        self.interview_storage.update_session(session_id, {"current_index": idx + 1})

        done = (idx + 1) >= len(questions)
        if done:
            self.interview_storage.update_session(session_id, {"status": "completed"})

        # Auto-show next question if not done
        next_question = None
        if not done:
            next_question = questions[idx + 1]

        return {
            "index": idx,
            "question": question_text,
            "answer": user_answer,
            "evaluation": evaluation,
            "next_index": idx + 1,
            "done": done,
            "next_question": next_question,
        }

    async def get_interview_results(self, session_id: str) -> Dict[str, Any]:
        session = self.interview_storage.get_session(session_id)
        if not session:
            return {"error": "Không tìm thấy phiên phỏng vấn"}
        return {
            "session_id": session_id,
            "source": session.get("source"),
            "keywords": session.get("keywords", []),
            "questions": session.get("questions", []),
            "interactions": session.get("interactions", []),
            "status": session.get("status", "in_progress"),
            "total_questions": len(session.get("questions", [])),
            "answered": len(session.get("interactions", [])),
        }

    def get_tools(self):
        start_interview_tool = FunctionTool.from_defaults(
            async_fn = self.start_interview,
            name = "start_interview",
            description = start_interview_tool_desc,
        )
        submit_answer_tool = FunctionTool.from_defaults(
            async_fn = self.submit_interview_answer,
            name = "submit_interview_answer",
            description = submit_answer_tool_desc,
        )
        get_results_tool = FunctionTool.from_defaults(
            async_fn = self.get_interview_results,
            name = "get_interview_results",
            description = get_results_tool_desc,
        )

        return [
            start_interview_tool,
            submit_answer_tool,
            get_results_tool,
        ]
    