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
    def _initialize_qa_retriever(self):
        db = chromadb.PersistentClient(path=vectorstore_path)
        chroma_collection = db.get_or_create_collection("question_collection")
        total_count = chroma_collection.count()
        print(f"Total questions in 'question_collection': {total_count}")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        return VectorIndexRetriever(index=index, similarity_top_k=10)
    

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
            original_text = getattr(node, "text", None)
            if not original_text and hasattr(node, "node"):
                # LlamaIndex NodeWithScore case
                inner = getattr(node, "node", None)
                original_text = getattr(inner, "text", None) if inner is not None else None

            # Fallbacks
            if not original_text:
                return node

            prompt = f"""
Bạn là chuyên gia phỏng vấn kỹ thuật. Hãy chỉnh sửa câu hỏi sau cho:
- Rõ ràng, đi vào tình huống/thực hành thay vì hỏi định nghĩa
- Phù hợp với kinh nghiệm ứng viên
- Giữ đúng chủ đề gốc, không mở rộng quá mức
- Ngắn gọn 1 câu, tiếng Việt
Kinh nghiệm ứng viên:
{user_project}
Câu hỏi gốc:
{original_text}
Câu hỏi đã cải thiện:
""".strip()

            result = self.llm.complete(prompt=prompt)
            improved = result.text.strip() if getattr(result, "text", None) else str(result).strip()
            if not improved:
                return node

            # Build a new node instead of mutating (NodeWithScore.text is read-only)
            try:
                base = getattr(node, "node", None)
                score = getattr(node, "score", None)
                metadata = {}
                if base is not None and hasattr(base, "metadata"):
                    metadata = dict(getattr(base, "metadata", {}) or {})
                else:
                    metadata = dict(getattr(node, "metadata", {}) or {})
                metadata["refined"] = True
                new_text_node = TextNode(text=improved, metadata=metadata)
                new_node = NodeWithScore(node=new_text_node, score=score)
            except Exception as inner_e:
                from types import SimpleNamespace
                new_node = SimpleNamespace(text=improved, metadata=dict(getattr(node, "metadata", {}) or {}))
            print(f"Câu hỏi đã cải thiện: {getattr(new_node, 'text', '')}")
            return new_node
        except Exception as e:
            # In case of any failure, return original node
            print(f"Lỗi khi cải thiện câu hỏi: {e}")
            return node


    async def qa_information(self, query: str) -> str:
        nodes = await self.qa_retriever.aretrieve(query)
        if not nodes:
            return "No relevant information found in the QA."
        return "\n\n---\n\n".join(
            f"Lĩnh vực: {node.metadata['source']} ID câu hỏi: {node.metadata['index']} Nội dung câu hỏi: {node.text}" for node in nodes
        )
    async def evaluate_user_answer(self, question: str, user_answer: str, source: str) -> str:
        """
        Đánh giá câu trả lời của người dùng dựa trên đáp án mẫu trong metadata của câu hỏi.

        Args:
            question: Câu hỏi phỏng vấn cần đánh giá.
            user_answer: Câu trả lời của ứng viên.

        Returns:
            Văn bản phản hồi có cấu trúc gồm: điểm (0-10), nhận xét ngắn, và 3 gợi ý cải thiện.
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
            return "Không tìm thấy câu hỏi phù hợp để đối chiếu đáp án. Vui lòng cung cấp rõ câu hỏi."

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
            return "Không có đáp án mẫu trong dữ liệu cho câu hỏi này để đánh giá."

        eval_prompt = f"""
Bạn là chuyên gia phỏng vấn. Hãy chấm điểm và nhận xét câu trả lời của ứng viên.
Câu hỏi: {question}
Đáp án mẫu (ground-truth): {reference_answer}
Câu trả lời của ứng viên: {user_answer}
Yêu cầu:
- Chấm điểm trên thang 0-10 (điểm số duy nhất).
- Tham khảo đáp án mẫu và kiến thức chuyên môn để chấm, ứng viên có thể trả lời khác đáp án nhưng vẫn đúng thì đạt điểm cao.
- Đánh giá dựa trên các tiêu chí: Tính phù hợp, Mức độ khó, Tính rõ ràng,...
- Nêu gợi ý cải thiện cụ thể, hành động được.
Định dạng trả về:
Điểm: <số từ 0 đến 10> (Chỉ 1 giá trị nguyên, không có dấu phẩy, không hiển thị /10)
Nhận xét: <đoạn ngắn> (Không nhận xét về câu trả lời mẫu VD Không được nhận xét như sau câu trả lời của ứng viên giống với đáp án mẫu)
Cải thiện:
- <gợi ý 1>
- <gợi ý 2>
- <gợi ý 3>
ví dụ:
Điểm: 8
Nhận xét: Trả lời chính xác, đầy đủ, rõ ràng và phù hợp với câu hỏi tuy nhiên có thể cải thiện thêm bằng cách thêm ví dụ, chi tiết hơn.
Cải thiện:
- Làm thêm các bài tập về các khái niệm và thuật toán liên quan
- Tìm hiểu thêm về các ứng dụng thực tế của các khái niệm và thuật toán liên quan
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

    def _get_retriever_by_source(self) -> VectorIndexRetriever:
        self.qa_retriever = self._initialize_qa_retriever()
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
            question_text = getattr(node, 'text', '')
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
        keywords = await self._generate_keywords(plan, user_project, job_description, number)
        retriever = self._get_retriever_by_source()
        collected: Dict[str, Dict[str, Any]] = {}
        print(f"Generated {len(keywords)} keywords: {keywords}")
        for i, kw in enumerate(keywords):
            try:
                result = await retriever.aretrieve(kw)
                #xử lí list câu hỏi để chọn câu phù hợp với CV và JD nhất
                nodes = result if isinstance(result, list) else [result] if result else []
                if nodes:
                    #chọn câu hỏi phù hợp với CV và JD nhất
                    selected_node = await self.re_rank_nodes(nodes, user_project, job_description, collected)
                    if selected_node:
                        nodes = [selected_node]  # Convert single node back to list for processing
                    else:
                        nodes = []
            except Exception as e:
                print(f"Error retrieving for keyword '{kw}': {e}")
                nodes = []
                
            for node in nodes:
                if not node:
                    continue
                # Defensive checks in case of unexpected shapes
                node_text = getattr(node, "text", None)
                if not node_text:
                    continue
                text_key = node_text.strip()
                if not text_key or text_key in collected:
                    continue
                collected[text_key] = {
                    "text": node_text,
                    "metadata": dict(getattr(node, "metadata", {}) or {}),
                }

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
            user_project=user_project
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
        # Use the source parameter passed in, fallback to session source if needed
        session_source = session.get("source", "Software_QA")
        source_to_use = source if source else session_source

        evaluation = await self.evaluate_user_answer(question_text, user_answer, source_to_use)

        self.interview_storage.append_interaction(
            session_id=session_id,
            question=question_text,
            answer=user_answer,
            evaluation=evaluation,
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
    