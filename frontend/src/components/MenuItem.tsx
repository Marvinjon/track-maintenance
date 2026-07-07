import { makeStyles } from "tss-react/mui";
import { ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import { Link } from "react-router-dom";

const useStyles = makeStyles()(() => ({
  menuItemText: {
    whiteSpace: "nowrap",
  },
}));

type MenuItemProps = {
  title: string;
  link: string;
  icon: React.ReactNode;
  selected?: boolean;
  onNavigate?: () => void;
};

export default function MenuItem({ title, link, icon, selected, onNavigate }: MenuItemProps) {
  const { classes } = useStyles();
  return (
    <ListItemButton component={Link} to={link} selected={selected} onClick={onNavigate}>
      <ListItemIcon>{icon}</ListItemIcon>
      <ListItemText primary={title} className={classes.menuItemText} />
    </ListItemButton>
  );
}
