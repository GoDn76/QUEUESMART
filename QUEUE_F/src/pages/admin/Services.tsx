import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchServices, createService } from "@/api/admin";
import { useForm } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function Services() {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['adminServices'],
    queryFn: fetchServices,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: createService,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminServices'] });
      setIsAddOpen(false);
      reset();
    }
  });

  const { register, handleSubmit, reset } = useForm<{ name: string; estimated_duration_minutes: number; priority_weight: number }>();

  const onSubmit = (formData: any) => {
    // Convert string inputs to numbers
    createMutation.mutate({
      name: formData.name,
      estimated_duration_minutes: Number(formData.estimated_duration_minutes),
      priority_weight: Number(formData.priority_weight)
    });
  };
  const services = data || [];  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-3xl font-semibold tracking-tight">Services</h3>
          <p className="text-muted-foreground text-sm mt-1">Configure service types offered at your location.</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-2" /> Add Service</Button>
          </DialogTrigger>
          <DialogContent className="bg-[#111113] border border-white/5 text-white sm:max-w-[425px]">
            <form onSubmit={handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle>Add New Service</DialogTitle>
                <DialogDescription>
                  Define a new service type with SLA and priority weight.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Service Name</label>
                  <input {...register("name", { required: true })} className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" placeholder="General Checkup" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Est. Duration (minutes)</label>
                  <input {...register("estimated_duration_minutes", { required: true, min: 1 })} type="number" className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" placeholder="15" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[#A1A1AA]">Priority Weight</label>
                  <input {...register("priority_weight", { required: true, min: 1, max: 200 })} type="number" className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" placeholder="10 (Normal), 100 (High)" required />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Create Service
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
              <TableHead>Service Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Token Prefix</TableHead>
              <TableHead>Target SLA</TableHead>
              <TableHead>Priority Level</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={6} className="text-center py-4">Loading...</TableCell></TableRow>
            ) : services.map((svc) => (
              <TableRow key={svc.id}>
                <TableCell className="font-medium">S-{(svc.id).toString().padStart(2, '0')}</TableCell>
                <TableCell>{svc.name}</TableCell>
                <TableCell>{svc.name.charAt(0).toUpperCase()}</TableCell>
                <TableCell>{svc.estimated_duration_minutes} min</TableCell>
                <TableCell className={svc.priority_weight >= 50 ? 'text-destructive font-medium' : ''}>
                  {svc.priority_weight >= 50 ? 'High' : 'Normal'}
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm">Edit</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
