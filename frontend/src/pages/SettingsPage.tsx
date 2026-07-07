import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import {
  BUILTIN_CURRENCIES,
  CUSTOM_CURRENCY_OPTION,
  type CurrencySelection,
  useCurrency,
} from "../hooks/useCurrency";
import { useColorScheme, type ColorSchemePreference } from "../hooks/useColorScheme";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";

export default function SettingsPage() {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const { preference, setPreference } = useColorScheme();
  const { selection, customCode, setSelection, setCustomCode } = useCurrency();

  return (
    <Container maxWidth="xs" className={classes.container}>
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">{strings.settings.display}</Typography>
        </AccordionSummary>
        <AccordionDetails className={classes.details}>
          <FormControl fullWidth>
            <InputLabel>{strings.settings.theme}</InputLabel>
            <Select
              label={strings.settings.theme}
              value={preference}
              onChange={(e) => setPreference(e.target.value as ColorSchemePreference)}
            >
              <MenuItem value="light">{strings.settings.themeLight}</MenuItem>
              <MenuItem value="dark">{strings.settings.themeDark}</MenuItem>
              <MenuItem value="system">{strings.settings.themeSystem}</MenuItem>
            </Select>
          </FormControl>
        </AccordionDetails>
      </Accordion>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">{strings.settings.regional}</Typography>
        </AccordionSummary>
        <AccordionDetails className={classes.details}>
          <FormControl fullWidth>
            <InputLabel>{strings.settings.currency}</InputLabel>
            <Select
              label={strings.settings.currency}
              value={selection}
              onChange={(e) => setSelection(e.target.value as CurrencySelection)}
            >
              {BUILTIN_CURRENCIES.map((code) => (
                <MenuItem key={code} value={code}>
                  {code}
                </MenuItem>
              ))}
              <MenuItem value={CUSTOM_CURRENCY_OPTION}>{strings.settings.currencyOther}</MenuItem>
            </Select>
          </FormControl>
          {selection === CUSTOM_CURRENCY_OPTION && (
            <TextField
              label={strings.settings.currencyCustom}
              value={customCode}
              onChange={(e) => setCustomCode(e.target.value)}
              helperText={strings.settings.currencyCustomHint}
              inputProps={{ maxLength: 3 }}
              fullWidth
              size="small"
            />
          )}
        </AccordionDetails>
      </Accordion>
    </Container>
  );
}
