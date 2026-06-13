import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function Settings() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h3 className="text-3xl font-semibold tracking-tight">Settings</h3>
        <p className="text-muted-foreground text-sm mt-1">Manage your organization's global configuration.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Organization Details</CardTitle>
          <CardDescription>Update your facility's name and contact information.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Facility Name</label>
            <Input defaultValue="City Hospital" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Contact Email</label>
            <Input defaultValue="admin@cityhospital.com" />
          </div>
        </CardContent>
        <CardFooter className="border-t border-border pt-4">
          <Button>Save Changes</Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Queue Configuration</CardTitle>
          <CardDescription>Global settings for token generation and wait times.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Token Reset Time</label>
            <Input defaultValue="00:00" type="time" />
            <p className="text-xs text-muted-foreground">Tokens will reset to T-001 at this time daily.</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Auto-Skip Timeout (Minutes)</label>
            <Input defaultValue="5" type="number" />
            <p className="text-xs text-muted-foreground">Tokens not responded to within this timeframe will be automatically marked as Skipped.</p>
          </div>
        </CardContent>
        <CardFooter className="border-t border-border pt-4">
          <Button>Save Changes</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
