"use client";

import { useRunState } from "@/lib/useRunState";
import { Card, Chip, PageTitle, SectionTitle, ScoreGauge, NoRunNotice } from "@/components/ui";

export default function EvaluationPage() {
  const { runId, state, loading, error } = useRunState();

  if (!runId) return <NoRunNotice />;
  if (loading) return <p className="text-sm text-black/50">Loading...</p>;
  if (error || !state) return <p className="text-sm text-rose-600">{error}</p>;

  const evaluation = state.evaluation_v1;
  const ats = state.ats_result;
  const hasEvaluation = "compatibility_score" in evaluation;
  const hasAts = "ats_score" in ats;

  if (!hasEvaluation) return <NoRunNotice />;

  return (
    <div>
      <PageTitle>Evaluation Dashboard</PageTitle>

      <div className="flex flex-wrap gap-8 mb-6">
        <ScoreGauge label="Compatibility" value={evaluation.compatibility_score} />
        {hasAts && <ScoreGauge label="ATS Score" value={ats.ats_score} />}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <SectionTitle>Missing Keywords</SectionTitle>
          <div className="flex flex-wrap gap-1.5">
            {evaluation.missing_keywords.map((k) => (
              <Chip key={k} tone="warn">
                {k}
              </Chip>
            ))}
            {evaluation.missing_keywords.length === 0 && (
              <span className="text-sm text-black/40">None</span>
            )}
          </div>
        </Card>

        <Card>
          <SectionTitle>Red Flags</SectionTitle>
          <ul className="text-sm space-y-1.5 list-disc list-inside text-black/80 dark:text-white/80">
            {evaluation.red_flags.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
            {evaluation.red_flags.length === 0 && <li className="list-none text-black/40">None</li>}
          </ul>
        </Card>

        {hasAts && (
          <>
            <Card>
              <SectionTitle>ATS: Flagged Sections</SectionTitle>
              <ul className="text-sm space-y-1.5 list-disc list-inside text-black/80 dark:text-white/80">
                {ats.flagged_sections.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
                {ats.flagged_sections.length === 0 && (
                  <li className="list-none text-black/40">None</li>
                )}
              </ul>
            </Card>

            <Card>
              <SectionTitle>ATS: Keyword Density Notes</SectionTitle>
              <ul className="text-sm space-y-1.5 list-disc list-inside text-black/80 dark:text-white/80">
                {ats.keyword_density_notes.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
                {ats.keyword_density_notes.length === 0 && (
                  <li className="list-none text-black/40">None</li>
                )}
              </ul>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
