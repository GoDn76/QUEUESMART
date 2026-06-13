import { useState, useEffect } from "react";
import { Bell, RefreshCw, Send, CheckCircle2, XCircle } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

const API_BASE = "http://localhost:8000/api/v1";

export default function Notifications() {
  const token = useAuthStore(state => state.token);
  const [provider, setProvider] = useState<string>("Unknown");
  const [status, setStatus] = useState<"UP" | "DOWN" | "LOADING">("LOADING");
  const [testPhone, setTestPhone] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sendResult, setSendResult] = useState<{success: boolean, msg: string} | null>(null);

  const fetchStatus = async () => {
    setStatus("LOADING");
    try {
      const res = await fetch(`${API_BASE}/health`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setProvider(data.notification_provider || "Unknown");
      setStatus(data.provider_status || "DOWN");
    } catch (err) {
      console.error(err);
      setStatus("DOWN");
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleSendTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testPhone) return;
    setIsSending(true);
    setSendResult(null);

    try {
      const res = await fetch(`${API_BASE}/admin/test-notification`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ phone: testPhone })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setSendResult({ success: true, msg: "Test message sent successfully!" });
      } else {
        setSendResult({ success: false, msg: "Failed to send test message." });
      }
    } catch (err) {
      console.error(err);
      setSendResult({ success: false, msg: "Error connecting to server." });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifications Settings</h1>
          <p className="text-[#A1A1AA] text-sm mt-1">Manage and test your notification provider</p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={status === "LOADING"}
          className="flex items-center gap-2 px-4 py-2 bg-[#27272A] hover:bg-[#3F3F46] text-white rounded-md text-sm font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${status === "LOADING" ? "animate-spin" : ""}`} />
          Refresh Status
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Status Card */}
        <div className="bg-[#18181B] border border-white/5 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-[#27272A] rounded-lg">
              <Bell className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-lg font-medium">Provider Status</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <p className="text-sm text-[#A1A1AA] mb-1">Current Provider</p>
              <div className="font-mono text-white bg-[#09090B] px-3 py-2 rounded-md border border-white/5 uppercase inline-block">
                {provider}
              </div>
            </div>
            
            <div>
              <p className="text-sm text-[#A1A1AA] mb-1">Connection Status</p>
              <div className="flex items-center gap-2">
                {status === "LOADING" ? (
                  <div className="flex items-center gap-2 text-yellow-500">
                    <RefreshCw className="w-4 h-4 animate-spin" /> Checking...
                  </div>
                ) : status === "UP" ? (
                  <div className="flex items-center gap-2 text-green-500">
                    <CheckCircle2 className="w-5 h-5" /> Online & Connected
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-red-500">
                    <XCircle className="w-5 h-5" /> Offline or Error
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Test Message Card */}
        <div className="bg-[#18181B] border border-white/5 rounded-xl p-6">
          <h2 className="text-lg font-medium mb-4">Send Test Message</h2>
          <form onSubmit={handleSendTest} className="space-y-4">
            <div>
              <label className="block text-sm text-[#A1A1AA] mb-1">Phone Number</label>
              <input
                type="text"
                value={testPhone}
                onChange={(e) => setTestPhone(e.target.value)}
                placeholder="+919876543210 or whatsapp:+1..."
                className="w-full bg-[#09090B] border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder-[#52525B] focus:outline-none focus:ring-2 focus:ring-white/20"
                required
              />
            </div>
            
            <button
              type="submit"
              disabled={isSending || status !== "UP" || !testPhone}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-white hover:bg-zinc-200 text-black rounded-md text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              {isSending ? "Sending..." : "Send Test Notification"}
            </button>
            
            {sendResult && (
              <div className={`p-3 rounded-md text-sm flex items-center gap-2 ${sendResult.success ? "bg-green-500/10 text-green-500 border border-green-500/20" : "bg-red-500/10 text-red-500 border border-red-500/20"}`}>
                {sendResult.success ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {sendResult.msg}
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
