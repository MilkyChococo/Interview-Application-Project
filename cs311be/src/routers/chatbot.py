
from src.services.service import Service
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage
from src.schemas.chatbot import ResponseChat, ChatbotMessage, InputChatbotMessage
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from src.services.service import Service
from src.routers.dependencies import get_service
from src.engines.preprocess_query import TextPreprocessor
from src.prompts.default_answer import not_supported_language
from src.services.report_service import generate_interview_report_pdf
from src.storage.interview_storage import InterviewStorage
from src.engines.llm_engine import LLMEngine
from fastapi import UploadFile, File, Form, HTTPException
import os
from openai import AzureOpenAI
from fastapi import (
    APIRouter, 
    Depends, 
)
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from fastapi.responses import StreamingResponse
from io import BytesIO
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone

import os
from dotenv import load_dotenv
load_dotenv()

TOKEN_LIMIT = int(os.getenv("TOKEN_LIMIT", 10000))

def format_resume_data_for_agent(resume_data: dict) -> str:
    """Format resume data into readable text for agent to understand candidate background"""
    if not resume_data:
        return ""
    
    text_parts = []
    
    # Personal Info
    if resume_data.get("name"):
        text_parts.append(f"Name: {resume_data.get('name')}")
    if resume_data.get("title"):
        text_parts.append(f"Title/Position: {resume_data.get('title')}")
    if resume_data.get("summary"):
        text_parts.append(f"Summary: {resume_data.get('summary')}")
    
    # Work Experience
    if resume_data.get("work_experience"):
        text_parts.append("\nWork Experience:")
        for exp in resume_data.get("work_experience", []):
            exp_text = f"- {exp.get('role', 'N/A')} at {exp.get('company', 'N/A')}"
            if exp.get("from_date") or exp.get("to_date"):
                exp_text += f" ({exp.get('from_date', '')} - {exp.get('to_date', 'Present')})"
            if exp.get("description"):
                for desc in exp.get("description", []):
                    if desc:
                        exp_text += f"\n  • {desc}"
            text_parts.append(exp_text)
    
    # Projects
    if resume_data.get("projects"):
        text_parts.append("\nProjects:")
        for proj in resume_data.get("projects", []):
            proj_text = f"- {proj.get('name', 'N/A')}"
            if proj.get("type"):
                proj_text += f" ({proj.get('type')})"
            if proj.get("description"):
                for desc in proj.get("description", []):
                    if desc:
                        proj_text += f"\n  • {desc}"
            text_parts.append(proj_text)
    
    # Skills
    if resume_data.get("skill_section"):
        text_parts.append("\nSkills:")
        for skill_group in resume_data.get("skill_section", []):
            if skill_group.get("name") and skill_group.get("skills"):
                skills_list = ", ".join([s for s in skill_group.get("skills", []) if s])
                text_parts.append(f"- {skill_group.get('name')}: {skills_list}")
    
    # Education
    if resume_data.get("education"):
        text_parts.append("\nEducation:")
        for edu in resume_data.get("education", []):
            edu_text = f"- {edu.get('degree', 'N/A')} from {edu.get('university', 'N/A')}"
            if edu.get("courses"):
                courses_list = ", ".join([c for c in edu.get("courses", []) if c])
                if courses_list:
                    edu_text += f"\n  Relevant courses: {courses_list}"
            text_parts.append(edu_text)
    
    return "\n".join(text_parts)

def format_job_data_for_agent(job_data: dict) -> str:
    """Format job data into readable text for agent to understand job requirements"""
    if not job_data:
        return ""
    
    text_parts = []
    
    # Job Title
    if job_data.get("job_title"):
        text_parts.append(f"Job Title: {job_data.get('job_title')}")
    
    # Company
    if job_data.get("company_name"):
        text_parts.append(f"Company: {job_data.get('company_name')}")
    
    # Job Purpose
    if job_data.get("job_purpose"):
        text_parts.append(f"\nJob Purpose: {job_data.get('job_purpose')}")
    
    # Required Skills (V2 format)
    if job_data.get("required_skills"):
        text_parts.append("\nRequired Skills:")
        for skill_group in job_data.get("required_skills", []):
            if skill_group.get("group_name"):
                text_parts.append(f"\n{skill_group.get('group_name')}:")
                for req in skill_group.get("requirements", []):
                    if req:
                        text_parts.append(f"  • {req}")
    
    # Keywords
    if job_data.get("keywords"):
        keywords_list = ", ".join([k for k in job_data.get("keywords", []) if k])
        if keywords_list:
            text_parts.append(f"\nKeywords: {keywords_list}")
    
    # Job Duties
    if job_data.get("job_duties_and_responsibilities"):
        text_parts.append("\nJob Duties and Responsibilities:")
        for duty in job_data.get("job_duties_and_responsibilities", []):
            if duty:
                text_parts.append(f"  • {duty}")
    
    # Required Qualifications
    if job_data.get("required_qualifications"):
        text_parts.append("\nRequired Qualifications:")
        for qual in job_data.get("required_qualifications", []):
            if qual:
                text_parts.append(f"  • {qual}")
    
    # Preferred Qualifications
    if job_data.get("preferred_qualifications"):
        text_parts.append("\nPreferred Qualifications:")
        for qual in job_data.get("preferred_qualifications", []):
            if qual:
                text_parts.append(f"  • {qual}")
    
    return "\n".join(text_parts)

def extract_user_project_from_resume(resume_data: dict) -> str:
    """Extract user projects and skills from resume data for start_interview tool"""
    if not resume_data:
        return ""
    
    project_parts = []
    
    # Extract projects with descriptions
    if resume_data.get("projects"):
        for proj in resume_data.get("projects", []):
            proj_text = f"{proj.get('name', '')}"
            if proj.get("type"):
                proj_text += f" ({proj.get('type')})"
            if proj.get("description"):
                descriptions = [d for d in proj.get("description", []) if d]
                if descriptions:
                    proj_text += ": " + "; ".join(descriptions)
            if proj_text:
                project_parts.append(proj_text)
    
    # Extract work experience
    if resume_data.get("work_experience"):
        for exp in resume_data.get("work_experience", []):
            exp_text = f"{exp.get('role', '')} at {exp.get('company', '')}"
            if exp.get("description"):
                descriptions = [d for d in exp.get("description", []) if d]
                if descriptions:
                    exp_text += ": " + "; ".join(descriptions)
            if exp_text:
                project_parts.append(exp_text)
    
    # Extract skills
    if resume_data.get("skill_section"):
        skills_list = []
        for skill_group in resume_data.get("skill_section", []):
            if skill_group.get("skills"):
                skills_list.extend([s for s in skill_group.get("skills", []) if s])
        if skills_list:
            project_parts.append(f"Skills: {', '.join(skills_list)}")
    
    return "\n".join(project_parts)

def extract_job_description_text(job_data: dict) -> str:
    """Extract job description text from job data for start_interview tool"""
    if not job_data:
        return ""
    
    desc_parts = []
    
    if job_data.get("job_title"):
        desc_parts.append(f"Position: {job_data.get('job_title')}")
    
    if job_data.get("job_purpose"):
        desc_parts.append(f"Purpose: {job_data.get('job_purpose')}")
    
    # Required Skills
    if job_data.get("required_skills"):
        for skill_group in job_data.get("required_skills", []):
            if skill_group.get("group_name") and skill_group.get("requirements"):
                reqs = [r for r in skill_group.get("requirements", []) if r]
                if reqs:
                    desc_parts.append(f"{skill_group.get('group_name')}: {'; '.join(reqs)}")
    
    # Job Duties
    if job_data.get("job_duties_and_responsibilities"):
        duties = [d for d in job_data.get("job_duties_and_responsibilities", []) if d]
        if duties:
            desc_parts.append(f"Responsibilities: {'; '.join(duties)}")
    
    # Qualifications
    if job_data.get("required_qualifications"):
        quals = [q for q in job_data.get("required_qualifications", []) if q]
        if quals:
            desc_parts.append(f"Required Qualifications: {'; '.join(quals)}")
    
    return "\n".join(desc_parts)

# --- MongoDB Atlas Cloud Connection (cùng với Database Router) ---
uri = os.getenv("USERDB_URI")
userdb_cluster_name = os.getenv("USERDB_CLUSTER_NAME")
userdb_name = os.getenv("USERDB_NAME")
client = MongoClient(uri)
db = client[userdb_cluster_name]
fs = gridfs.GridFS(db)

# Collections for chat data (sử dụng cùng database với Database Router)
chat_files_collection = db["chat_files"]
users_collection = db[userdb_name]  # Cùng collection users với Database Router

# JWT Configuration (same as database_router)
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Azure/OpenAI config helpers ---
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview").strip()
AZURE_OPENAI_WHISPER_DEPLOYMENT = os.getenv("AZURE_OPENAI_WHISPER_DEPLOYMENT", "").strip()

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current authenticated user from JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        exp = payload.get("exp")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # Kiểm tra token có hết hạn không
        if exp and datetime.now(timezone(timedelta(hours=7))).timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token has expired")
            
        # Get user from database
        user = users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user["full_name"]
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_openai_client_for_audio():
    """Create OpenAI client configured for either Azure OpenAI or OpenAI.

    Returns:
        (client, model_name)
        - client: OpenAI instance
        - model_name: model/deployment to be used for audio transcription
    """
    # Prefer Azure OpenAI when endpoint and key are set
    client = AzureOpenAI(
        api_key="8Ix1GDGlYBdcyRrsk3GJ7Q5ThI0BEjcARMuM4Zsw1OrTFQ0ZNIZOJQQJ99BHACHYHv6XJ3w3AAAAACOGFiFP",
        api_version="2024-02-01",
        azure_endpoint="https://triet-me9pksqj-eastus2.openai.azure.com/"
    )
    return client, AZURE_OPENAI_WHISPER_DEPLOYMENT

chatbot_router = APIRouter(
    tags=["chat"],
    prefix="/chat",
)

@chatbot_router.post("/prepare-interview")
async def prepare_interview(
    session_id: str = Form(...),
    service: Service = Depends(get_service),
    current_user: dict = Depends(get_current_user)
):
    """Prepare CV and JD extraction before starting chat"""
    try:
        print(f"Preparing interview for session: {session_id}, user: {current_user['email']}")
        
        # Get user data
        user = users_collection.find_one({"email": current_user["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Initialize ResumeJobStorage for this session
        from src.storage.resume_storage import ResumeJobStorage
        resume_job_storage = ResumeJobStorage()
        
        # Check if CV and JD are already extracted for this session
        session_context = resume_job_storage.get_session_context(session_id)
        resume_data = session_context.resume_data
        job_data = session_context.job_data
        
        # Extract CV if not already done
        if not resume_data and user.get("resume_id"):
            print("Extracting CV data...")
            try:
                # Get resume file from GridFS
                resume_id = ObjectId(user["resume_id"])
                resume_file = fs.get(resume_id)
                
                # Create a mock UploadFile object for the service
                from fastapi import UploadFile
                import io
                file_content = resume_file.read()  # Đọc nội dung từ GridOut
                
                # Create UploadFile with proper content type
                class MockUploadFile(UploadFile):
                    def __init__(self, file, filename="resume.pdf"):
                        super().__init__(file)
                        self._filename = filename
                    
                    @property
                    def filename(self):
                        return self._filename
                    
                    @filename.setter
                    def filename(self, value):
                        self._filename = value

                resume_file_obj = MockUploadFile(
                    io.BytesIO(file_content),  # Truyền bytes content, không phải GridOut
                    "resume.pdf"
                )
                
                # Extract CV data
                resume_data = await service.resume_flow_service.extract_cv(resume_file_obj)
                
                # Save to resume_storage
                resume_job_storage.save_resume_data(session_id, resume_data)
                print("CV extracted and saved successfully")
                
            except Exception as e:
                print(f"Error extracting CV: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to extract CV: {str(e)}")
        
        # Extract JD if not already done
        if not job_data and user.get("jd_text"):
            print("Extracting JD data...")
            try:
                # Extract job data
                job_data = await service.resume_flow_service.extract_job_details(user["jd_text"])
                
                # Save to resume_storage
                resume_job_storage.save_job_data(session_id, job_data)
                print("JD extracted and saved successfully")
                
            except Exception as e:
                print(f"Error extracting JD: {str(e)}")
                resume_job_storage.save_job_data(session_id, job_data)
        
        # Get updated session context
        session_context = resume_job_storage.get_session_context(session_id)
        resume_data = session_context.resume_data
        job_data = session_context.job_data
        
        # Check if both CV and JD are ready
        if not resume_data:
            raise HTTPException(status_code=400, detail="CV not found. Please upload your resume first.")
        print(f"Interview preparation completed for session: {session_id}")
        
        return {
            "message": "Interview preparation completed successfully",
            "session_id": session_id,
            "resume_data": resume_data,
            "job_data": job_data,
            "ready_for_chat": True
        }
        
    except Exception as e:
        print(f"Error preparing interview: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.post("/extract-cv/")
async def extract_cv(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    service: Service = Depends(get_service)
    # current_user: dict = Depends(get_current_user)  # Optional: uncomment if auth required
):
    """Extract CV content and store in database for session"""
    try:
        # Extract CV using resume flow service
        resume_data = await service.resume_flow_service.extract_cv(file)
        
        # Save to resume_storage
        from src.storage.resume_storage import ResumeJobStorage
        resume_job_storage = ResumeJobStorage()
        resume_job_storage.save_resume_data(session_id, resume_data)
        
        return {
            "message": "CV extracted and stored successfully",
            "resume_data": resume_data,
            "session_id": session_id
        }
    except Exception as e:
        print(f"Error extracting CV: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.post("/extract-job/")
async def extract_job(
    job_description: str = Form(...),
    session_id: str = Form(...),
    service: Service = Depends(get_service)
    # current_user: dict = Depends(get_current_user)  # Optional: uncomment if auth required
):
    """Extract job description and store in database for session"""
    try:
        # Extract JD using resume flow service
        job_data = await service.resume_flow_service.extract_job_details_v2(job_description, None)
        
        # Save to resume_storage
        from src.storage.resume_storage import ResumeJobStorage
        resume_job_storage = ResumeJobStorage()
        resume_job_storage.save_job_data(session_id, job_data)
        
        return {
            "message": "Job details extracted and stored successfully",
            "job_data": job_data,
            "session_id": session_id
        }
    except Exception as e:
        print(f"Error extracting job description: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.get("/session-context/{session_id}")
async def get_session_context(session_id: str):
    """Get CV and JD data for a session (no auth required for debugging)"""
    try:
        from src.storage.resume_storage import ResumeJobStorage
        resume_job_storage = ResumeJobStorage()
        session_context = resume_job_storage.get_session_context(session_id)
        
        return {
            "session_id": session_id,
            "has_resume_data": bool(session_context.resume_data),
            "has_job_data": bool(session_context.job_data),
            "resume_data": session_context.resume_data,
            "job_data": session_context.job_data
        }
    except Exception as e:
        print(f"Error getting session context: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.get("/extraction-status/{session_id}")
async def get_extraction_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Check if CV and JD are extracted for this session"""
    try:
        # Get user data
        user = users_collection.find_one({"email": current_user["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get session context from resume_storage
        from src.storage.resume_storage import ResumeJobStorage
        resume_job_storage = ResumeJobStorage()
        session_context = resume_job_storage.get_session_context(session_id)
        
        # Check extraction status
        has_resume_file = bool(user.get("resume_id"))
        has_jd_text = bool(user.get("jd_text"))
        has_resume_data = bool(session_context.resume_data)
        has_job_data = bool(session_context.job_data)
        
        return {
            "session_id": session_id,
            "has_resume_file": has_resume_file,
            "has_jd_text": has_jd_text,
            "has_resume_data": has_resume_data,
            "has_job_data": has_job_data,
            "ready_for_chat": has_resume_data and has_job_data,
            "resume_data": session_context.resume_data,
            "job_data": session_context.job_data
        }
        
    except Exception as e:
        print(f"Error checking extraction status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.post("/chatDomain")
async def chat_with_agent(
    request: InputChatbotMessage, 
    service: Service = Depends(get_service),
    # current_user: dict = Depends(get_current_user)
):
    """Chat with agent using stored CV/JD context from resume_storage"""
    memory = ChatMemoryBuffer(token_limit=TOKEN_LIMIT)
    user_message = request.query
    session_id = request.room_id
    
    # Detect short chat early to allow chatting without CV/JD
    text_preprocessor = TextPreprocessor()
    # determine if message is short chat (greeting/brief) so we can bypass CV/JD requirement
    is_short_chat = bool(text_preprocessor.detect_short_chat(text_preprocessor.replace_abbreviations(user_message)))
    preprocessed_message, lang = text_preprocessor.preprocess_text(user_message)
    
    # Get stored CV and JD data from resume_storage
    from src.storage.resume_storage import ResumeJobStorage
    resume_job_storage = ResumeJobStorage()
    session_context = resume_job_storage.get_session_context(session_id)
    resume_data = session_context.resume_data
    job_data = session_context.job_data
    
    # Debug logging
    print(f"[DEBUG] Session ID: {session_id}")
    print(f"[DEBUG] Resume data exists: {bool(resume_data)}")
    print(f"[DEBUG] Job data exists: {bool(job_data)}")
    
    # Format CV and JD data for agent understanding
    formatted_resume = format_resume_data_for_agent(resume_data) if resume_data else ""
    formatted_job = format_job_data_for_agent(job_data) if job_data else ""
    
    # Extract user_project and job_description for start_interview tool
    user_project_text = extract_user_project_from_resume(resume_data) if resume_data else ""
    job_description_text = extract_job_description_text(job_data) if job_data else ""
    
    print(f"[DEBUG] Formatted resume length: {len(formatted_resume)}")
    print(f"[DEBUG] Formatted job length: {len(formatted_job)}")
    print(f"[DEBUG] User project text length: {len(user_project_text)}")
    print(f"[DEBUG] Job description text length: {len(job_description_text)}")
    
    # ALWAYS load CV/JD data into memory (not just for non-short chats)
    # This ensures agent always has context available
    context_messages = []
    
    # CRITICAL: Add session_id/room_id context FIRST so agent knows what session_id to use
    context_messages.append(
        ChatMessage(
            role="system",
            content=f"""[SESSION_CONTEXT]
room_id = "{session_id}"
session_id = "{session_id}"

IMPORTANT: When calling ANY tool, you MUST use session_id="{session_id}" exactly as shown above.
- For start_interview: use session_id="{session_id}"
- For submit_interview_answer: use session_id="{session_id}" (THE SAME value!)
- For get_interview_results: use session_id="{session_id}"

DO NOT create a new session_id. DO NOT modify this value. Use it exactly as provided."""
        )
    )
    print(f"[DEBUG] Added session_id context: {session_id}")
    
    # Add CV information to memory
    if formatted_resume:
        context_messages.append(
            ChatMessage(
                role="user",
                content=f"[CANDIDATE_RESUME]\n{formatted_resume}\n\nUse this resume information to understand the candidate's background, skills, experience, and projects when creating the interview plan. When calling start_interview tool, use the following user_project: {user_project_text}"
            )
        )
        print(f"[DEBUG] Added CV to memory")
    
    # Add JD information to memory
    if formatted_job:
        context_messages.append(
            ChatMessage(
                role="user",
                content=f"[JOB_DESCRIPTION]\n{formatted_job}\n\nUse this job description to understand the position requirements and create an interview plan that matches the job requirements. When calling start_interview tool, use the following job_description: {job_description_text}"
            )
        )
        print(f"[DEBUG] Added JD to memory")
    
    # Add confirmation message only if we have data
    if formatted_resume and formatted_job:
        context_messages.append(
            ChatMessage(
                role="assistant",
                content=f"I have received both the candidate's resume and job description. I will analyze them and create a personalized interview plan. The session_id for this interview is: {session_id}. When you say 'Start', I will call start_interview with session_id='{session_id}'."
            )
        )
    elif formatted_resume:
        context_messages.append(
            ChatMessage(
                role="assistant",
                content=f"I have received the candidate's resume. The session_id is: {session_id}. I will use this information to create an interview plan."
            )
        )
    elif formatted_job:
        context_messages.append(
            ChatMessage(
                role="user",
                content="I have the job description but need the candidate's resume to create a personalized interview plan. Please ask the candidate to upload their CV."
            )
        )
    
    # Load CV/JD context FIRST, before conversation history
    # This ensures CV/JD context is always available to the agent
    if context_messages:
        memory.put_messages(context_messages)
        print(f"[DEBUG] Loaded {len(context_messages)} context messages into memory for session: {session_id}")
    else:
        print(f"[DEBUG] WARNING: No CV/JD data found for session: {session_id}")
    
    # Load conversation history AFTER CV/JD context

    conversation_histories = service.chatbot_mess_mgmt.get_conversation_history(session_id)
    memory.put_messages(conversation_histories)
    if lang == "Others":
        return ResponseChat(
            response=not_supported_language,
            is_outdomain=False
        )  
    else:
        reply = await service.chatbot.handle_query(
            query=preprocessed_message,
            memory=memory
        )
    #reply = await service.chatbot.handle_query(query=user_message, memory=memory)

    chat_message = ChatbotMessage(
        session_id=session_id,
        chat_message=user_message,
        answer=reply,
        datetime=datetime.now(),
    )
    service.chatbot_mess_mgmt.insert_chat_record(chat_message)
    return ResponseChat(
        response=reply
    )


@chatbot_router.get("/final-report/{session_id}")
async def get_final_report(session_id: str, service: Service = Depends(get_service)):
    """Generate a final interview PDF report with 2 sections:
    overall assessment and per-question details table.
    """
    try:
        storage = InterviewStorage()
        session = storage.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")

        # Parse per-question evaluation text to extract score and improvements if present
        interactions = []
        import re as _re
        for item in session.get("interactions", []) or []:
            evaluation_text = item.get("evaluation", "") or ""
            # Try to extract score like: "Điểm: 8/10" or "Điểm: 8"
            score_match = _re.search(r"(?i)điểm\s*:\s*(\d+(?:[\./]\d+)?)", evaluation_text)
            score_val = score_match.group(1) if score_match else ""
            # Try to extract improvement bullets after a line starting with "Cải thiện" or similar
            improvements = []
            improvements_block = _re.split(r"(?i)cải\s*thiện\s*:?", evaluation_text)
            if len(improvements_block) > 1:
                # take after the keyword; split by lines starting with dash
                tail = improvements_block[1]
                for line in tail.splitlines():
                    if line.strip().startswith("-"):
                        improvements.append(line.strip().lstrip("- "))

            interactions.append({
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "evaluation": evaluation_text,
                "improvements": improvements,
                "score": score_val,
            })

        # Build overall section using LLM summarization over evaluations and answers
        llm = LLMEngine().openai_llm
        summary_prompt = (
            "Bạn là chuyên gia tuyển dụng. Hãy tóm tắt tổng quan năng lực của ứng viên dựa trên các đánh giá sau (tiếng Việt, 4-6 câu).\n\n" +
            "\n\n".join(f"- {i.get('evaluation','')}" for i in interactions if i.get('evaluation'))
        )
        strengths_prompt = (
            "Từ các đánh giá sau, liệt kê 3-5 điểm mạnh ngắn gọn (gạch đầu dòng, tiếng Việt).\n\n" +
            "\n\n".join(f"- {i.get('evaluation','')}" for i in interactions if i.get('evaluation'))
        )
        improvements_prompt = (
            "Từ các đánh giá sau, liệt kê 3-5 điểm cần cải thiện ngắn gọn (gạch đầu dòng, tiếng Việt).\n\n" +
            "\n\n".join(f"- {i.get('evaluation','')}" for i in interactions if i.get('evaluation'))
        )
        fitness_prompt = (
            "Dựa trên các đánh giá, viết 1-2 câu về mức độ phù hợp vị trí của ứng viên (tiếng Việt).\n\n" +
            "\n\n".join(f"- {i.get('evaluation','')}" for i in interactions if i.get('evaluation'))
        )

        def _llm_text(prompt: str) -> str:
            try:
                r = llm.complete(prompt=prompt)
                return getattr(r, "text", str(r))
            except Exception:
                return ""

        overall = {
            "summary": _llm_text(summary_prompt).strip(),
            "strengths": [s.strip("- ") for s in _llm_text(strengths_prompt).splitlines() if s.strip()],
            "improvements": [s.strip("- ") for s in _llm_text(improvements_prompt).splitlines() if s.strip()],
            "fitness": _llm_text(fitness_prompt).strip(),
        }

        results = {"overall": overall, "interactions": interactions}
        pdf_bytes = generate_interview_report_pdf(results)
        # FastAPI Response import omitted in file header, return raw bytes via dict base64 if needed.
        # To keep current code style, return as base64 string to client to download
        import base64
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return {"filename": f"interview_report_{session_id}.pdf", "content_type": "application/pdf", "data_base64": b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.get("/evaluation-data/{session_id}")
async def get_evaluation_data(session_id: str, service: Service = Depends(get_service)):
    """Get interview evaluation data as JSON for frontend display"""
    try:
        print(f"Getting evaluation data for session: {session_id}")
        
        storage = InterviewStorage()
        session = storage.get_session(session_id)
        if not session:
            print(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        print(f"Found session: {session.get('session_id')}, status: {session.get('status')}")
        
        # Don't update user_id since we removed authentication requirement
        print(f"Processing session {session_id}")
        # Parse per-question evaluation text to extract score and improvements
        interactions = []
        session_interactions = session.get("interactions", []) or []
        print(f"Found {len(session_interactions)} interactions in session")
        
        import re as _re
        for item in session_interactions:
            evaluation_text = item.get("evaluation", "") or ""
            # Try to extract score like: "Điểm: 8/10" or "Điểm: 8"
            score_match = _re.search(r"(?i)điểm\s*:\s*(\d+(?:[\./]\d+)?)", evaluation_text)
            score_val = score_match.group(1) if score_match else "0"
            
            # Convert score to percentage (assuming 10-point scale)
            try:
                if "/" in score_val:
                    score_num = float(score_val.split("/")[0])
                    max_score = float(score_val.split("/")[1])
                    score_percentage = int((score_num / max_score) * 100)
                else:
                    score_percentage = int(float(score_val) * 10)  # Convert to percentage
            except:
                score_percentage = 0
            
            # Try to extract improvement bullets
            improvements = []
            improvements_block = _re.split(r"(?i)cải\s*thiện\s*:?", evaluation_text)
            if len(improvements_block) > 1:
                tail = improvements_block[1]
                for line in tail.splitlines():
                    if line.strip().startswith("-"):
                        improvements.append(line.strip().lstrip("- "))

            # Extract strengths from evaluation text
            strengths = []
            strengths_block = _re.split(r"(?i)điểm\s*mạnh\s*:?", evaluation_text)
            if len(strengths_block) > 1:
                tail = strengths_block[1]
                for line in tail.splitlines():
                    if line.strip().startswith("-"):
                        strengths.append(line.strip().lstrip("- "))

            interactions.append({
                "id": len(interactions) + 1,
                "question": item.get("question", ""),
                "userAnswer": item.get("answer", ""),
                "aiFeedback": {
                    "score": score_percentage,
                    "strengths": strengths if strengths else ["Good technical knowledge", "Clear communication"],
                    "improvements": improvements if improvements else ["Could provide more specific examples"],
                    "suggestion": evaluation_text
                }
            })

        # Calculate overall score
        if interactions:
            overall_score = sum(q["aiFeedback"]["score"] for q in interactions) // len(interactions)
        else:
            overall_score = 0

        # Get session metadata
        questions = session.get("questions", [])
        created_at = session.get("created_at")
        
        # Calculate duration (mock for now)
        duration = "25 minutes"  # Could be calculated from timestamps
        
        # Generate title based on source
        source = session.get("source", "Software Engineer")
        title = f"{source} Interview"

        # Format date safely
        try:
            if created_at and hasattr(created_at, 'strftime'):
                formatted_date = created_at.strftime("%B %d, %Y")
            else:
                formatted_date = "Today"
        except Exception as date_error:
            print(f"Error formatting date: {date_error}")
            formatted_date = "Today"

        result = {
            "title": title,
            "date": formatted_date,
            "duration": duration,
            "overallScore": overall_score,
            "questions": interactions,
            "sessionId": session_id,
        }
        print(f"Successfully processed evaluation data: {len(interactions)} questions, overall score: {overall_score}")
        return result
    except Exception as e:
        print(f"Error in get_evaluation_data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("vi"),
):
    """Transcribe audio to text only - no chat processing"""
    try:
        client, model_name = create_openai_client_for_audio()
        audio_bytes = await file.read()
        result = client.audio.transcriptions.create(
            model=model_name,
            file=(file.filename or "audio.webm", audio_bytes),
            language=language,
            response_format="text"
        )
        return {"text": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

@chatbot_router.get("/interview-sessions")
async def get_interview_sessions(
    service: Service = Depends(get_service),
    current_user: dict = Depends(get_current_user)
):
    """Get list of completed interview sessions for current user"""
    try:
        print(f"Current user: {current_user}")
        # Get user ID from email (current_user is email from JWT)
        user_doc = users_collection.find_one({"email": current_user["email"]})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = str(user_doc["_id"])
        print(f"User id: {user_id}")
        # Get all sessions for current user from InterviewStorage
        from src.storage.interview_storage import InterviewStorage
        interview_storage = InterviewStorage()
        user_sessions = interview_storage.find_sessions_by_user_id(user_id)
        print(f"Found {len(user_sessions)} sessions for user {user_id}")
        
        # Get session metadata and filter completed sessions for current user
        session_list = []
        for session_doc in user_sessions:
            try:
                # Extract session_id from session document
                session_id = session_doc.get("session_id")
                if not session_id:
                    continue
                    
                # Check if this session is completed by looking at InterviewStorage
                from src.storage.interview_storage import InterviewStorage
                interview_storage = InterviewStorage()
                session_data = interview_storage.get_session(session_id)
                
                # Only include sessions that are explicitly marked as completed
                if session_data and session_data.get("status") == "completed":
                    # Get session context to check if it has CV/JD data
                    session_context = service.resume_job_storage.get_session_context(session_id)
                    
                    # Get conversation history for metadata
                    conversation_histories = service.chatbot_mess_mgmt.get_conversation_history(session_id)
                    
                    # Get session metadata
                    session_metadata = service.resume_job_storage.get_session_metadata(session_id)
                    
                    # Determine session title from source or job data
                    title = "Mock Interview"
                    
                    # First try to get source from session data
                    if session_data and session_data.get("source"):
                        title = f"{session_data['source']} Interview"
                    
                    # If no source found, try to extract from job data
                    if title == "Mock Interview" and session_context.job_data:
                        job_data_str = str(session_context.job_data)
                        if "title" in job_data_str.lower() or "position" in job_data_str.lower():
                            # Try to extract job title (simplified)
                            title = "Software Engineer Interview"  # Default for now
                    
                    # Get date safely - prefer actual interview start time
                    created_at = None
                    
                    # Try to get actual interview start time from conversation history
                    try:
                        # Get raw conversation data to access datetime
                        raw_conversations = service.chatbot_mess_mgmt.aggregate_conversation_by_session_id(session_id)
                        if raw_conversations:
                            # Get the first message datetime as interview start time
                            first_message = raw_conversations[0]
                            if hasattr(first_message, 'datetime'):
                                created_at = first_message.datetime
                    except Exception as e:
                        print(f"Error getting interview start time: {e}")
                    
                    # Fallback to session metadata from MongoDB Atlas
                    if created_at is None:
                        created_at = session_doc.get("created_at") if session_doc else None
                    
                    # Final fallback to current time
                    if created_at is None:
                        created_at = datetime.now()
                    
                    session_list.append({
                        "session_id": session_id,
                        "user_id": user_id,
                        "title": title,
                        "date": created_at,
                        "duration": session_metadata.get("duration", "25 min"),
                        "message_count": len(conversation_histories),
                        "has_cv": bool(session_context.resume_data),
                        "has_jd": bool(session_context.job_data),
                        "status": "completed"
                    })
            except Exception as session_error:
                # Skip problematic sessions and continue
                session_id_str = session_doc.get("session_id", "unknown") if session_doc else "unknown"
                print(f"Error processing session {session_id_str}: {session_error}")
                continue
        
        # Sort by date (most recent first)
        session_list.sort(key=lambda x: x["date"], reverse=True)
        
        return {"sessions": session_list}
    except Exception as e:
        print(f"Error in get_interview_sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chatbot_router.post("/voice-chat")
async def voice_chat(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    language: str = Form("vi"),
    service: Service = Depends(get_service),
):
    """
    Voice chat endpoint:
      - Nhận audio từ frontend
      - Gọi OpenAI Whisper (hoặc model audio) để chuyển audio -> text
      - Gửi text đó vào cùng luồng xử lý như /chatDomain
      - Trả về cả transcript và câu trả lời của agent
    """
    try:
        client, model_name = create_openai_client_for_audio()
        audio_bytes = await file.read()
        result = client.audio.transcriptions.create(
            model=model_name,
            file=(file.filename or "audio.webm", audio_bytes),
            language=language,
            response_format="text"
        )
        transcript_text = getattr(result, "text", "") or ""
        if not transcript_text:
            raise RuntimeError("Empty transcript returned")

        # Dùng lại logic của /chatDomain bằng cách tạo InputChatbotMessage
        chat_request = InputChatbotMessage(
            room_id=session_id,
            query=transcript_text,
        )

        # Gọi trực tiếp hàm chat_with_agent để tái sử dụng toàn bộ logic mock interview
        chat_response: ResponseChat = await chat_with_agent(chat_request, service)  # type: ignore[arg-type]

        # Trả về cả transcript và câu trả lời của agent
        return {
            "transcript": transcript_text,
            "chat_response": chat_response,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice chat failed: {e}")

