import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: ("ADMIN" | "OPERATOR")[];
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { token, role } = useAuthStore();
  const location = useLocation();

  if (!token || !role) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    // If they are an operator trying to access admin, send to workspace
    if (role === "OPERATOR") {
      return <Navigate to="/operator" replace />;
    }
    // If admin trying to access operator, send to dashboard
    return <Navigate to="/admin" replace />;
  }

  return <>{children}</>;
}
