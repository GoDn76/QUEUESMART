import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { login } from "@/api/auth";
import { LayoutDashboard, Lock, User, Loader2, Monitor } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const navigate = useNavigate();
  const location = useLocation();
  
  // Dynamically determine login type based on route
  const isOperator = location.pathname.includes('/operator');
  const loginType = isOperator ? 'OPERATOR' : 'ADMIN';

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      await login(email, password, loginType);
      
      if (loginType === 'ADMIN') {
        navigate("/admin");
      } else {
        navigate("/operator");
      }
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response.data.detail || "Counter already controlled by another active operator.");
      } else if (err.response?.status === 401) {
        setError(err.response.data.detail || "Invalid credentials or too many failed attempts.");
      } else {
        setError("An error occurred during login. The backend may be offline.");
      }
    } finally {
      setLoading(false);
    }
  };

  const autofill = () => {
    setEmail(loginType === 'ADMIN' ? 'admin@test.com' : 'operator@test.com');
    setPassword("password123");
  };

  const Icon = isOperator ? Monitor : LayoutDashboard;
  const accentColor = isOperator ? "bg-[#4ADE80]" : "bg-[#FACC15]";
  const shadowColor = isOperator ? "shadow-[0_0_30px_rgba(74,222,128,0.2)]" : "shadow-[0_0_30px_rgba(250,204,21,0.2)]";
  const hoverText = isOperator ? "text-[#4ADE80]" : "text-[#FACC15]";

  return (
    <div className="theme-operations dark min-h-screen flex w-full bg-[#050505] text-[#FFFFFF] font-sans antialiased selection:bg-[#4ADE80] selection:text-black">
      {/* Left side - Branding / Image */}
      <div className="hidden lg:flex w-1/2 bg-[#111111] relative items-center justify-center overflow-hidden border-r border-[#27272A]">
        <div className={`absolute inset-0 ${isOperator ? 'bg-[#4ADE80]/5' : 'bg-[#FACC15]/5'} z-10`}></div>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#1A1A1A] via-[#050505] to-[#050505] z-0"></div>
        <div className="z-20 text-center space-y-6 max-w-md px-8">
          <div className={`w-20 h-20 ${accentColor} rounded-md flex items-center justify-center mx-auto ${shadowColor}`}>
            <Icon className="w-10 h-10 text-black" />
          </div>
          <h1 className="text-5xl font-black tracking-tight text-[#FFFFFF]">QueueMind</h1>
          <p className="text-xl text-[#888888]">
            {isOperator ? "Operator Mission Control Access Terminal." : "The next-generation smart queue management system for modern enterprises."}
          </p>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-[#050505]">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-[#FFFFFF]">Welcome back</h2>
            <p className="text-[#888888] mt-2">Enter your credentials to access your workspace</p>
          </div>

          <div className="bg-[#111111] border border-[#27272A] p-8 rounded-md shadow-2xl relative overflow-hidden">
            {isOperator && <div className="absolute top-0 left-0 w-full h-1 bg-[#4ADE80]"></div>}
            {!isOperator && <div className="absolute top-0 left-0 w-full h-1 bg-[#FACC15]"></div>}
            
            <div className="mb-6 pb-4 border-b border-[#27272A] flex justify-between items-center">
              <span className="text-sm font-bold uppercase tracking-widest text-[#888888]">
                {isOperator ? "Operator Login" : "Admin Login"}
              </span>
              <button 
                type="button" 
                onClick={() => navigate(isOperator ? "/admin/login" : "/operator/login")}
                className={`text-xs ${hoverText} hover:underline font-bold tracking-wider`}
              >
                Switch to {isOperator ? "Admin" : "Operator"}
              </button>
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              {error && (
                <div className="p-3 text-sm text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 rounded-md">
                  {error}
                </div>
              )}
              
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#888888]">Email address</label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 w-5 h-5 text-[#888888]" />
                    <Input 
                      type="email" 
                      placeholder={isOperator ? "operator@cityhospital.com" : "admin@cityhospital.com"}
                      className="pl-10 h-12 bg-[#1A1A1A] border-[#27272A] text-white rounded-md focus:border-[#4ADE80] focus:ring-[#4ADE80]"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-medium text-[#888888]">Password</label>
                    <a href="#" className={`text-xs ${hoverText} hover:underline`}>Forgot password?</a>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 w-5 h-5 text-[#888888]" />
                    <Input 
                      type="password" 
                      placeholder="••••••••" 
                      className="pl-10 h-12 bg-[#1A1A1A] border-[#27272A] text-white rounded-md focus:border-[#4ADE80] focus:ring-[#4ADE80]"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              <Button type="submit" className="w-full h-12 text-lg font-black uppercase tracking-widest bg-[#FFFFFF] hover:bg-gray-200 text-black rounded-md transition-all active:scale-95" disabled={loading}>
                {loading ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
                Secure Access
              </Button>
            </form>

            <div className="mt-8 pt-6 border-t border-[#27272A]">
              <p className="text-sm text-[#888888] text-center mb-4 uppercase tracking-widest font-bold">Test Credentials</p>
              <div className="w-full">
                <Button variant="outline" className="w-full border-[#27272A] hover:bg-[#1A1A1A] text-white rounded-md" onClick={autofill}>
                  Autofill {isOperator ? "Operator" : "Admin"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
