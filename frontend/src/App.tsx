import { BrowserRouter, Route, Routes } from "react-router-dom";
import { LandingPage } from "./pages/LandingPage";
import { InterviewSetupPage } from "./pages/InterviewSetupPage";
import { InterviewPage } from "./pages/InterviewPage";
import { ReportPage } from "./pages/ReportPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/setup" element={<InterviewSetupPage />} />
        <Route path="/interview/:interviewId" element={<InterviewPage />} />
        <Route path="/interview/:interviewId/report" element={<ReportPage />} />
      </Routes>
    </BrowserRouter>
  );
}
