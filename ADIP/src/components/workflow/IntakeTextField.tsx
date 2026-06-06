import { TextField } from '@mui/material';
import type { TextFieldProps } from '@mui/material';
import { colors } from '../../theme/colors';

export function IntakeTextField(props: TextFieldProps) {
  return (
    <TextField
      size="small"
      fullWidth
      sx={{
        '& .MuiOutlinedInput-root': {
          bgcolor: colors.bg.glass,
          fontSize: '0.8125rem',
        },
        ...props.sx,
      }}
      {...props}
    />
  );
}
