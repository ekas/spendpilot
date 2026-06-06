import type { ApplicantInput } from "@/lib/api";

export interface ApplicantFormValues {
  name: string;
  monthly_income: number;
  monthly_expenses: number;
  requested_amount: number;
  existing_debt: number;
  credit_utilization_percent: number;
  delinquencies_12m: number;
  employment_months: number;
  overdrafts_90d: number;
  income_verified: boolean;
}

interface ApplicantDetailsFormProps {
  value: ApplicantFormValues;
  onChange: (value: ApplicantFormValues) => void;
  disabled?: boolean;
}

const fields: Array<{
  key: Exclude<keyof ApplicantFormValues, "income_verified">;
  label: string;
  min: number;
  max?: number;
  step?: number;
}> = [
  { key: "monthly_income", label: "Monthly income", min: 1, step: 100 },
  { key: "monthly_expenses", label: "Monthly expenses", min: 0, step: 100 },
  { key: "requested_amount", label: "Requested amount", min: 1, step: 500 },
  { key: "existing_debt", label: "Outstanding debt", min: 0, step: 100 },
  {
    key: "credit_utilization_percent",
    label: "Credit utilization (%)",
    min: 0,
    max: 100,
    step: 1,
  },
  {
    key: "delinquencies_12m",
    label: "Late payments (12 months)",
    min: 0,
    step: 1,
  },
  {
    key: "employment_months",
    label: "Employment history (months)",
    min: 0,
    step: 1,
  },
  {
    key: "overdrafts_90d",
    label: "Overdrafts (90 days)",
    min: 0,
    step: 1,
  },
];

export function toApplicantInput(
  values: ApplicantFormValues
): ApplicantInput {
  return {
    name: values.name,
    monthly_income: values.monthly_income,
    monthly_expenses: values.monthly_expenses,
    requested_amount: values.requested_amount,
    existing_debt: values.existing_debt,
    credit_utilization: values.credit_utilization_percent / 100,
    delinquencies_12m: values.delinquencies_12m,
    employment_months: values.employment_months,
    overdrafts_90d: values.overdrafts_90d,
    income_verified: values.income_verified,
  };
}

export function ApplicantDetailsForm({
  value,
  onChange,
  disabled,
}: ApplicantDetailsFormProps) {
  return (
    <fieldset disabled={disabled} className="mb-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="sm:col-span-2 lg:col-span-4">
          <span className="mb-1.5 block text-xs font-medium text-muted-foreground">
            Applicant reference
          </span>
          <input
            value={value.name}
            onChange={(event) =>
              onChange({ ...value, name: event.target.value })
            }
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none transition focus:border-accent"
            autoComplete="off"
          />
        </label>

        {fields.map((field) => (
          <label key={field.key}>
            <span className="mb-1.5 block text-xs font-medium text-muted-foreground">
              {field.label}
            </span>
            <input
              type="number"
              value={value[field.key]}
              min={field.min}
              max={field.max}
              step={field.step}
              onChange={(event) =>
                onChange({
                  ...value,
                  [field.key]: Number(event.target.value),
                })
              }
              className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none transition focus:border-accent"
            />
          </label>
        ))}

        <label className="flex min-h-10 items-center gap-3 self-end rounded-md border border-border px-3">
          <input
            type="checkbox"
            checked={value.income_verified}
            onChange={(event) =>
              onChange({
                ...value,
                income_verified: event.target.checked,
              })
            }
            className="h-4 w-4 accent-[var(--accent)]"
          />
          <span className="text-xs font-medium text-foreground">
            Income already verified
          </span>
        </label>
      </div>
    </fieldset>
  );
}
