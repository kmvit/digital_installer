import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ClockInPage from "./pages/ClockInPage";
import ClockOutPage from "./pages/ClockOutPage";
import EquipmentPage from "./pages/EquipmentPage";
import ObjectSelectPage from "./pages/ObjectSelectPage";
import ObjectWorkPage from "./pages/ObjectWorkPage";
import AddWorkPage from "./pages/AddWorkPage";
import DepartPage from "./pages/DepartPage";
import SummaryPage from "./pages/SummaryPage";
import ApprovalPage from "./pages/ApprovalPage";
import HistoryPage from "./pages/HistoryPage";
import ReportsPage from "./pages/ReportsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/clock-in" element={<ClockInPage />} />
        <Route path="/clock-out" element={<ClockOutPage />} />
        <Route path="/equipment" element={<EquipmentPage />} />
        <Route path="/objects" element={<ObjectSelectPage />} />
        <Route path="/object/:sessionId" element={<ObjectWorkPage />} />
        <Route path="/add-work/:sessionId" element={<AddWorkPage />} />
        <Route path="/depart/:sessionId" element={<DepartPage />} />
        <Route path="/summary/:workdayId" element={<SummaryPage />} />
        <Route path="/approval" element={<ApprovalPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/reports" element={<ReportsPage />} />
      </Route>
    </Routes>
  );
}
