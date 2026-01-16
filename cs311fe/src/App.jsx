import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import Home from "./pages/Home";
import Interview from "./pages/Interview";
import Upload from "./pages/Upload";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import Mock_Interview from "./pages/Mock_Interview";
import EvaluationReport from "./pages/EvaluationReport";

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/signin" element={<SignIn />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/interview" element={<Interview />} />
            <Route path="/mock" element={<Mock_Interview />} />
            <Route path="/evaluation-report" element={<EvaluationReport />} />
          </Routes>
        </main>
      </div>
    </AuthProvider>
  );
}

export default App;
