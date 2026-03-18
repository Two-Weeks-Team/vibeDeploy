"use client";

import { NodeDef } from "./pipeline-node";
import { buildEdgeCurve } from "./pipeline-edge";

export type ParticleRoute = string[];

export const PARTICLE_DUR_SECONDS = 12;
export const PARTICLE_DUR = "12s";

export const EVAL_PARTICLE_ROUTES: ParticleRoute[] = [
  ["input", "enrich"],
  ["enrich", "architect", "cross_exam"],
  ["enrich", "scout", "cross_exam"],
  ["enrich", "catalyst", "cross_exam"],
  ["enrich", "guardian", "cross_exam"],
  ["enrich", "advocate", "cross_exam"],
  ["cross_exam", "score_tech", "verdict"],
  ["cross_exam", "score_market", "verdict"],
  ["cross_exam", "score_innovation", "verdict"],
  ["cross_exam", "score_risk", "verdict"],
  ["cross_exam", "score_user", "verdict"],
  ["verdict", "decision"],
  ["decision", "fix_storm", "architect", "cross_exam"],
  ["decision", "fix_storm", "scout", "cross_exam"],
  ["decision", "fix_storm", "catalyst", "cross_exam"],
  ["decision", "fix_storm", "guardian", "cross_exam"],
  ["decision", "fix_storm", "advocate", "cross_exam"],
  ["decision", "scope_down", "doc_gen"],
  ["decision", "doc_gen", "blueprint", "prompt_strategy", "code_gen", "code_eval"],
  ["code_eval", "build_validate", "git_push", "ci_test", "app_spec", "do_build", "do_deploy", "verified"],
];

export const BS_PARTICLE_ROUTES: ParticleRoute[] = [
  ["input", "architect", "synthesize"],
  ["input", "scout", "synthesize"],
  ["input", "catalyst", "synthesize"],
  ["input", "guardian", "synthesize"],
  ["input", "advocate", "synthesize"],
];

export function buildParticlePath(nodes: NodeDef[], route: ParticleRoute) {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  let path = "";

  for (let index = 0; index < route.length - 1; index += 1) {
    const source = nodeMap.get(route[index]);
    const target = nodeMap.get(route[index + 1]);
    if (!source || !target) return null;
    path += `${index === 0 ? "" : " "}${buildEdgeCurve(source, target, index === 0)}`;
  }

  return path || null;
}

interface ParticleLayerProps {
  pipeline: "evaluation" | "brainstorm";
  nodes: NodeDef[];
}

export function ParticleLayer({ pipeline, nodes }: ParticleLayerProps) {
  const particlePaths = (pipeline === "evaluation" ? EVAL_PARTICLE_ROUTES : BS_PARTICLE_ROUTES)
    .map((route) => buildParticlePath(nodes, route))
    .filter((path): path is string => Boolean(path));

  return (
    <>
      {particlePaths.map((path, index) => {
        const begin = index === 0 ? "0s" : `-${(PARTICLE_DUR_SECONDS * index) / particlePaths.length}s`;
        const particleId = `p-${pipeline}-${index}`;
        return (
          <g key={particleId}>
            <circle r="0.38" fill="rgba(125,211,252,0.78)">
              <animateMotion dur={PARTICLE_DUR} begin={begin} repeatCount="indefinite" path={path} rotate="auto" />
            </circle>
            <circle r="1.1" fill="rgba(56,189,248,0.12)" filter="url(#particle-glow)">
              <animateMotion dur={PARTICLE_DUR} begin={begin} repeatCount="indefinite" path={path} rotate="auto" />
            </circle>
          </g>
        );
      })}
    </>
  );
}
