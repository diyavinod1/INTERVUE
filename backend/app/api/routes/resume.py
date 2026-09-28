"""
POST /api/resume/parse - lets the frontend preview the extracted profile
before the candidate commits to starting the interview (e.g. so the setup
page can show "here's what we found in your resume" as a sanity check).
This does NOT create a candidate/interview record; that only happens on
POST /api/interviews.
"""
from fastapi import APIRouter, File, UploadFile

from app.schemas.candidate import CandidateProfile
from app.services import interview_service, resume_service

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/parse", response_model=CandidateProfile)
async def parse_resume(resume: UploadFile = File(...)):
    raw_bytes = await resume.read()
    interview_service.validate_upload(resume, raw_bytes)
    text = resume_service.extract_text(resume.filename, raw_bytes)
    return resume_service.build_candidate_profile(text)
