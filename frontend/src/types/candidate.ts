export interface Project {
  name: string;
  description: string;
  technologies: string[];
}

export interface Experience {
  title: string;
  organization: string;
  duration: string;
  description: string;
}

export interface CandidateProfile {
  name: string;
  education: string[];
  experience: Experience[];
  skills: string[];
  technologies: string[];
  projects: Project[];
  internships: string[];
  certifications: string[];
  achievements: string[];
}

export interface JobProfile {
  target_role: string;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  technologies: string[];
  experience_requirement: string;
  key_technical_areas: string[];
}

export interface CreateInterviewResponse {
  interview_id: string;
  candidate_id: string;
  full_name: string;
  target_role: string;
  experience_level: string;
  resume_filename: string;
  resume_profile: CandidateProfile;
  job_profile: JobProfile;
}
