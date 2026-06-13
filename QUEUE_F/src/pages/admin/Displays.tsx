import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus } from "lucide-react";

const displays = [
  { id: 'D-01', location: 'Main Waiting Area', type: 'Global', status: 'Online', lastPing: '1m ago' },
  { id: 'D-02', location: 'Pharmacy Lobby', type: 'Service Specific', status: 'Online', lastPing: '1m ago' },
  { id: 'D-03', location: 'Emergency Room', type: 'Service Specific', status: 'Offline', lastPing: '2d ago' },
];

export default function Displays() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-3xl font-semibold tracking-tight">Display Boards</h3>
          <p className="text-muted-foreground text-sm mt-1">Manage public digital signage and TVs.</p>
        </div>
        <Button><Plus className="w-4 h-4 mr-2" /> Add Display</Button>
      </div>

      <div className="bg-card border border-border rounded-lg shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead>Display ID</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Content Type</TableHead>
              <TableHead>Last Ping</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displays.map((disp) => (
              <TableRow key={disp.id}>
                <TableCell className="font-medium">{disp.id}</TableCell>
                <TableCell>{disp.location}</TableCell>
                <TableCell>{disp.type}</TableCell>
                <TableCell className="text-muted-foreground">{disp.lastPing}</TableCell>
                <TableCell>
                  <Badge variant={disp.status === 'Online' ? 'default' : 'destructive'} 
                         className={disp.status === 'Online' ? 'bg-success hover:bg-success/80' : ''}>
                    {disp.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm">Configure</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
