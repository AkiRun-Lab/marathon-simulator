import pandas as pd
import numpy as np

class VDOTHandler:
    def __init__(self, vdot_list_path, vdot_pace_path=None):
        self.vdot_df = pd.read_csv(vdot_list_path)
        
        # Ensure 'Marathon' column exists or find it
        self.marathon_col = 'Marathon'
        if self.marathon_col not in self.vdot_df.columns:
            # Fallback search
            for col in self.vdot_df.columns:
                if 'Marathon' in col or 'Full' in col:
                    self.marathon_col = col
                    break
        
        if self.marathon_col not in self.vdot_df.columns:
            # Last resort: assume last column
            self.marathon_col = self.vdot_df.columns[-1]

    def get_vdot_options(self):
        """Returns list of available VDOTs for dropdown"""
        return sorted(self.vdot_df['VDOT'].astype(float).unique())

    def get_time_for_vdot(self, vdot):
        """Returns marathon time string for a given VDOT"""
        row = self.vdot_df[self.vdot_df['VDOT'] == vdot]
        if not row.empty:
            return row.iloc[0][self.marathon_col]
        return None

    def get_seconds_for_vdot(self, vdot):
        """Returns marathon time in seconds for a given VDOT"""
        t_str = self.get_time_for_vdot(vdot)
        if t_str:
            return self._time_str_to_seconds(t_str)
        return None

    def get_closest_vdot(self, target_time_str):
        """
        Find closest VDOT from target marathon time string.
        """
        target_seconds = self._time_str_to_seconds(target_time_str)
        if target_seconds == 0:
            return 45.0 # Default fallback
            
        # Calculate difference for all rows
        seconds_series = self.vdot_df[self.marathon_col].apply(self._time_str_to_seconds)
        idx = (seconds_series - target_seconds).abs().idxmin()
        return float(self.vdot_df.iloc[idx]['VDOT'])

    @staticmethod
    def _time_str_to_seconds(t_str):
        try:
            t_str = str(t_str).strip()
            parts = t_str.split(':')
            if len(parts) == 3: # h:mm:ss
                return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2: # m:ss (unlikely for marathon but possible for pace)
                return int(parts[0])*60 + int(parts[1])
            return 0
        except:
            return 0
