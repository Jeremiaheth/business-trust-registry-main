import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AboutPage } from "./pages/AboutPage";
import { BusinessProfilePage } from "./pages/BusinessProfilePage";
import { ContactPage } from "./pages/ContactPage";
import { DirectoryPage } from "./pages/DirectoryPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ReportPage } from "./pages/ReportPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/directory" element={<DirectoryPage />} />
        <Route path="/businesses/:btrId" element={<BusinessProfilePage />} />
        <Route path="/reports/:btrId" element={<ReportPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
