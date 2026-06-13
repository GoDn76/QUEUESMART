import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Plus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchServices } from "@/api/admin";

const fallbackServices = [
  { id: 1, name: 'Registration', estimated_duration_minutes: 5, priority_weight: 10 },
  { id: 2, name: 'Billing', estimated_duration_minutes: 8, priority_weight: 10 },
  { id: 3, name: 'Pharmacy', estimated_duration_minutes: 3, priority_weight: 10 },
  { id: 4, name: 'Emergency', estimated_duration_minutes: 15, priority_weight: 90 },
];

export default function Services() {
  const { data, isLoading } = useQuery({
    queryKey: ['adminServices'],
    queryFn: fetchServices,
    retry: false,
  });

  const services = data || fallbackServices;
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-3xl font-semibold tracking-tight">Services</h3>
          <p className="text-muted-foreground text-sm mt-1">Configure service types offered at your location.</p>
        </div>
        <Button><Plus className="w-4 h-4 mr-2" /> Add Service</Button>
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
