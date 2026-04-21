import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import LoginPage from "../pages/LoginPage";
import GatewayPage from "../pages/GatewayPage";
import WorkspacePage from "../pages/WorkspacePage";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/gateway" element={<GatewayPage />} />
        <Route path="/workspace/:section" element={<WorkspacePage />} />
        <Route path="/workspace" element={<Navigate to="/workspace/chatspace" replace />} />
        {/* Catch-all redirect to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Route>
    </Routes>
  );
}
