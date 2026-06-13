import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Plus, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDisplays, createDisplay } from "@/api/display";
import { useForm } from "react-hook-form";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export default function Displays() {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: displaysData, isLoading } = useQuery({
    queryKey: ['adminDisplays'],
    queryFn: fetchDisplays
  });

  const createMutation = useMutation({
    mutationFn: createDisplay,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminDisplays'] });
      setIsAddOpen(false);
      reset();
    }
  });

  const { register, handleSubmit, reset, watch } = useForm<{ name: string; board_type: "COUNTER" | "ORGANIZATION"; counter_id?: string }>();
  
  const onSubmit = (formData: any) => {
    createMutation.mutate({
      name: formData.name,
      board_type: formData.board_type,
      counter_id: formData.board_type === "COUNTER" ? Number(formData.counter_id) : undefined
    });
  };

  const displayList = displaysData || [];
  const selectedType = watch("board_type");

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-3xl font-semibold tracking-tight">Display Boards</h3>
          <p className="text-muted-foreground text-sm mt-1">Manage public digital signage and TVs.</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-2" /> Add Display</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <form onSubmit={handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle>Add New Display</DialogTitle>
                <DialogDescription>
                  Generate a secure UUID token for a new smart TV or tablet display.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Display Name</label>
                  <Input {...register("name", { required: true })} placeholder="Lobby Main TV" required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Board Type</label>
                  <select {...register("board_type", { required: true })} className="w-full h-10 px-3 py-2 rounded-md border border-input bg-background text-sm">
                    <option value="ORGANIZATION">Global (All Counters)</option>
                    <option value="COUNTER">Counter Specific</option>
                  </select>
                </div>
                {selectedType === "COUNTER" && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Counter ID</label>
                    <Input {...register("counter_id", { required: true })} type="number" placeholder="1" required />
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Create Board
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
              <TableHead>Display ID</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Content Type</TableHead>
              <TableHead>Last Ping</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">Loading displays...</TableCell>
              </TableRow>
            ) : displayList.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">No displays configured yet.</TableCell>
              </TableRow>
            ) : (
              displayList.map((disp: any) => (
                <TableRow key={disp.display_id}>
                  <TableCell className="font-medium text-xs font-mono">{disp.display_id.split('-')[0]}</TableCell>
                  <TableCell>{disp.name}</TableCell>
                  <TableCell>{disp.board_type}</TableCell>
                  <TableCell className="text-muted-foreground">Active</TableCell>
                  <TableCell>
                    <Badge className="bg-success hover:bg-success/80">Online</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => window.open(`/display/${disp.display_id}`, '_blank')}>Launch</Button>
                    <Button variant="ghost" size="sm" className="text-destructive">Revoke</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
