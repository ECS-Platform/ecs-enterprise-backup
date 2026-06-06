import { FormControl, InputLabel, MenuItem, Select } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import { colors } from '../../theme/colors';

interface IntakeSelectFieldProps {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (event: SelectChangeEvent<string>) => void;
}

export function IntakeSelectField({ label, options, value, onChange }: IntakeSelectFieldProps) {
  return (
    <FormControl size="small" fullWidth>
      <InputLabel sx={{ fontSize: '0.8125rem' }}>{label}</InputLabel>
      <Select
        label={label}
        value={value}
        onChange={onChange}
        sx={{
          bgcolor: colors.bg.glass,
          fontSize: '0.8125rem',
        }}
      >
        {options.map((opt) => (
          <MenuItem key={opt.value} value={opt.value} sx={{ fontSize: '0.8125rem' }}>
            {opt.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
