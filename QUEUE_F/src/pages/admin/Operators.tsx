import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchOperators } from "@/api/admin";

const fallbackOperators = [
  { id: 1, name: 'Sarah J.', email: 'sarah@test.com', active: true, session_version: 1, failed_login_attempts: 0 },
  { id: 2, name: 'Mike T.', email: 'mike@test.com', active: true, session_version: 1, failed_login_attempts: 0 },
  { id: 3, name: 'Emma W.', email: 'emma@test.com', active: false, session_version: 1, failed_login_attempts: 0 },
];

export default function Operators() {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ['adminOperators'],
    queryFn: fetchOperators,
    retry: false,
  });

  const operators = data || fallbackOperators;

  const handleAddOperator = (e: React.FormEvent) => {
    e.preventDefault();
    setIsAddOpen(false);
    // Trigger mutation or toaster in real app
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-3xl font-semibold tracking-tight">Operators</h3>
          <p className="text-muted-foreground text-sm mt-1">Manage staff members and view their performance.</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-2" /> Add Operator</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <form onSubmit={handleAddOperator}>
              <DialogHeader>
                <DialogTitle>Add New Operator</DialogTitle>
                <DialogDescription>
                  Create credentials for a new staff member. They will receive an email to set their password.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Full Name</label>
                  <Input placeholder="John Doe" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email Address</label>
                  <Input type="email" placeholder="john.doe@hospital.com" required />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit">Send Invitation</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-card border border-border rounded-lg shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead>Staff ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Handled Today</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={6} className="text-center py-4">Loading...</TableCell></TableRow>
            ) : operators.map((op) => (
              <TableRow key={op.id}>
                <TableCell className="font-medium">OP-{op.id}</TableCell>
                <TableCell>{op.name}</TableCell>
                <TableCell>{op.email}</TableCell>
                <TableCell>{op.failed_login_attempts}</TableCell>
                <TableCell>
                  <Badge variant={op.active ? 'default' : 'secondary'} 
                         className={op.active ? 'bg-success hover:bg-success/80' : ''}>
                    {op.active ? 'Active' : 'Disabled'}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm">View</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
