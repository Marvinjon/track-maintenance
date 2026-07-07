import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useColorScheme, type ColorSchemePreference } from "../hooks/useColorScheme";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";

export default function SettingsPage() {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const { preference, setPreference } = useColorScheme();

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
    </Container>
  );
}
