"use client";

import { useState, useCallback } from "react";
import { useIngestMutation } from "@/lib/hooks/use-ingest-mutation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  X,
} from "lucide-react";
import { toast } from "sonner";
import type { IngestResponse } from "@/lib/api/client";

export default function IngestPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dept, setDept] = useState("public");
  const [visibility, setVisibility] = useState("internal");
  const [baseTier, setBaseTier] = useState(1);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const mutation = useIngestMutation();

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === "application/pdf") {
      setFile(droppedFile);
      setResult(null);
    } else {
      toast.error("Only PDF files are supported");
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setResult(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    try {
      const response = await mutation.mutateAsync({
        file,
        dept,
        visibility,
        base_tier: baseTier,
      });
      setResult(response);
      if (response.status === "success") {
        toast.success("Document processed successfully");
      } else if (response.status === "partial") {
        toast.warning("Document partially processed — some sections flagged for review");
      }
    } catch {
      toast.error("Ingestion failed");
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Document Ingestion</h1>
        <p className="text-sm text-muted-foreground">
          Upload PDF documents to the knowledge base
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors ${
          dragActive
            ? "border-primary bg-primary/5"
            : "border-border/50 hover:border-border"
        }`}
      >
        {file ? (
          <div className="flex items-center gap-3">
            <FileText className="h-8 w-8 text-primary" />
            <div>
              <p className="text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => {
                setFile(null);
                setResult(null);
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <>
            <Upload className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Drag & drop a PDF file or{" "}
              <label className="cursor-pointer font-medium text-primary hover:underline">
                browse
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
            </p>
          </>
        )}
      </div>

      {/* Settings */}
      <Card className="border-border/50">
        <CardHeader className="pb-4">
          <CardTitle className="text-sm">Ingestion Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">Department</Label>
              <Select value={dept} onValueChange={(v) => v && setDept(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="finance">Finance</SelectItem>
                  <SelectItem value="hr">HR</SelectItem>
                  <SelectItem value="corp">Corp</SelectItem>
                  <SelectItem value="public">Public</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Visibility</Label>
              <Select value={visibility} onValueChange={(v) => v && setVisibility(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                  <SelectItem value="restricted">Restricted</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Source Reliability: {baseTier}</Label>
            <Slider
              value={[baseTier]}
              onValueChange={(v) => setBaseTier(Array.isArray(v) ? v[0] : v)}
              min={0}
              max={3}
              step={1}
            />
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>0 — Low</span>
              <span>3 — High</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Button
        onClick={handleSubmit}
        disabled={!file || mutation.isPending}
        className="w-full"
      >
        {mutation.isPending ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Upload className="mr-2 h-4 w-4" />
        )}
        Ingest Document
      </Button>

      {/* Result */}
      {result && (
        <Card
          className={`border ${
            result.status === "success"
              ? "border-emerald-500/30"
              : result.status === "partial"
                ? "border-yellow-500/30"
                : "border-destructive/30"
          }`}
        >
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              {result.status === "success" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-500 mt-0.5" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
              )}
              <div className="flex-1 space-y-2">
                <p className="text-sm font-medium">
                  {result.status === "success"
                    ? "Document processed successfully"
                    : result.status === "partial"
                      ? "Document partially processed"
                      : "Processing failed"}
                </p>
                <div className="flex gap-3 text-sm">
                  <Badge variant="secondary" className="gap-1">
                    <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                    {result.chunks_ingested} sections added
                  </Badge>
                  {result.chunks_quarantined > 0 && (
                    <Badge variant="secondary" className="gap-1 text-yellow-400">
                      <AlertTriangle className="h-3 w-3" />
                      {result.chunks_quarantined} flagged for review
                    </Badge>
                  )}
                </div>
                {result.errors.length > 0 && (
                  <div className="space-y-1">
                    {result.errors.map((err, i) => (
                      <p key={i} className="text-xs text-destructive">
                        Unable to process some content
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
