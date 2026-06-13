import * as z from "zod";

export const OrganizationCreateSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email format"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const UserLoginSchema = z.object({
  email: z.string().email("Invalid email format"),
  password: z.string().min(1, "Password is required"),
});

export const OperatorCreateSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email format"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  counter_id: z.number().int().positive("Must be a valid counter ID"),
});

export const CounterCreateSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  queue_type: z.enum(["FIFO", "PRIORITY", "HYBRID"]),
  qr_slug: z.string().min(3, "Slug must be at least 3 characters").regex(/^[a-z0-9-]+$/, "Only lowercase letters, numbers, and dashes allowed"),
});

export const ServiceTypeCreateSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  estimated_duration_minutes: z.number().int().positive("Must be positive"),
  priority_weight: z.number().int().positive("Must be positive"),
});

export const TokenCreateSchema = z.object({
  customer_name: z.string().min(2, "Name is required"),
  customer_phone: z.string().min(8, "Valid phone number required"),
  service_type_id: z.number().int().positive("Please select a service type"),
});
