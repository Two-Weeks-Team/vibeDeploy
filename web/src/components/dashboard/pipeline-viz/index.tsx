"use client";

import { PipelineGraph, PipelineGraphProps } from "./pipeline-graph";

export function PipelineViz(props: PipelineGraphProps) {
  return <PipelineGraph {...props} />;
}

export type { PipelineType } from "./pipeline-graph";
export type { NodeStatus } from "./pipeline-node";
