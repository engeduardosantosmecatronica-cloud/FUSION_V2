import { Toaster } from "@/components/ui/toaster";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { queryClientInstance } from "@/lib/query-client";
import PageNotFound from "./lib/PageNotFound";
import ScrollToTop from "./components/ScrollToTop";
import AppLayout from "@/components/layout/AppLayout";
import Home from "@/pages/Home";
import Market from "@/pages/Market";
import Chart from "@/pages/Chart";
import Signals from "@/pages/Signals";
import Orders from "@/pages/Orders";
import Portfolio from "@/pages/Portfolio";
import Analysis from "@/pages/Analysis";
import Strategies from "@/pages/Strategies";
import Backtest from "@/pages/Backtest";
import Simulation from "@/pages/Simulation";
import Events from "@/pages/Events";
import Reports from "@/pages/Reports";
import Logs from "@/pages/Logs";
import Health from "@/pages/Health";
import Settings from "@/pages/Settings";
import Help from "@/pages/Help";

function FusionRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/market" element={<Market />} />
        <Route path="/chart" element={<Chart />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/simulation" element={<Simulation />} />
        <Route path="/events" element={<Events />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/health" element={<Health />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
      </Route>
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClientInstance}>
      <Router>
        <ScrollToTop />
        <FusionRoutes />
      </Router>
      <Toaster />
    </QueryClientProvider>
  );
}