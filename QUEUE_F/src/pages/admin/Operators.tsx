import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Loader2, Trash2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchOperators, createOperator, deleteOperator } from "@/api/admin";
import { fetchCounters } from "@/api/counters";
import { useForm } from "react-hook-form";

export default function Operators() {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const queryClient = useQueryClient();
  
  const { data: counters } = useQuery({
    queryKey: ['countersList'],
    queryFn: fetchCounters,
  });
  
  const { data, isLoading } = useQuery({
    queryKey: ['adminOperators'],
    queryFn: fetchOperators,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: createOperator,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminOperators'] });
      setIsAddOpen(false);
      reset();
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteOperator,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminOperators'] });
    }
  });

  const { register, handleSubmit, reset } = useForm<{ name: string; email: string; password: string; counter_id: string }>();
  const operators = data || [];

  const onSubmit = (formData: any) => {
    createMutation.mutate({
      ...formData,
      counter_id: formData.counter_id ? Number(formData.counter_id) : undefined
    });
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
          <DialogContent className="bg-[#111113] border border-white/5 text-white sm:max-w-[425px]">
            <form onSubmit={handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle>Add New Operator</DialogTitle>
                <DialogDescription>
                  Create credentials for a new staff member. They will receive an email to set their password.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Full Name</label>
                  <input {...register("name", { required: true })} className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" placeholder="John Doe" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Email Address</label>
                  <input {...register("email", { required: true })} type="email" className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" placeholder="john.doe@hospital.com" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Password</label>
                  <input {...register("password", { required: true, minLength: 6 })} type="password" className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" placeholder="Minimum 6 characters" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Assign Counter (Required)</label>
                  <select 
                    {...register("counter_id", { required: true })}
                    className="w-full h-10 px-3 py-2 bg-[#1A1A1A] border border-[#27272A] rounded-md text-white focus:outline-none focus:border-[#4ADE80]"
                  >
                    <option value="">Select a counter...</option>
                    {counters?.map((c: any) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Send Invitation
                </Button>
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
                <TableCell className="text-right space-x-2">
                  <Button variant="ghost" size="sm">View</Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                    onClick={() => {
                      if(window.confirm(`Are you sure you want to delete operator ${op.name}?`)) {
                        deleteMutation.mutate(op.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
