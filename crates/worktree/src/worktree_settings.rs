use std::path::Path;

use anyhow::Context as _;
use settings::{RegisterSetting, ScanSymlinksSetting, Settings};
use util::{
    ResultExt,
    paths::{PathMatcher, PathStyle},
    rel_path::RelPath,
};

#[derive(Clone, PartialEq, Eq, RegisterSetting)]
pub struct WorktreeSettings {
    /// Whether to prevent this project from being shared in public channels.
    pub prevent_sharing_in_public_channels: bool,
    pub file_scan_exclusions: PathMatcher,
    pub file_scan_inclusions: PathMatcher,
    /// This field contains all ancestors of the `file_scan_inclusions`. It's used to
    /// determine whether to terminate worktree scanning for a given dir.
    pub parent_dir_scan_inclusions: PathMatcher,
    pub scan_symlinks: ScanSymlinksSetting,
    pub file_scan_depth: Option<u32>,
    pub private_files: PathMatcher,
    pub hidden_files: PathMatcher,
    pub read_only_files: PathMatcher,
}

impl WorktreeSettings {
    pub fn is_path_private(&self, path: &RelPath) -> bool {
        path.ancestors()
            .any(|ancestor| self.private_files.is_match(ancestor))
    }

    pub fn is_path_excluded(&self, path: &RelPath) -> bool {
        path.ancestors().any(|ancestor| {
            self.file_scan_exclusions.is_match(ancestor)
                || ancestor
                    .file_name()
                    .is_some_and(is_default_excluded_component)
        })
    }

    pub fn is_path_default_excluded(&self, path: &RelPath) -> bool {
        path.ancestors().any(|ancestor| {
            ancestor
                .file_name()
                .is_some_and(is_default_excluded_component)
        })
    }

    pub fn is_path_always_included(&self, path: &RelPath, is_dir: bool) -> bool {
        if is_dir {
            self.parent_dir_scan_inclusions.is_match(path)
        } else {
            self.file_scan_inclusions.is_match(path)
        }
    }

    pub fn is_path_hidden(&self, path: &RelPath) -> bool {
        path.ancestors()
            .any(|ancestor| self.hidden_files.is_match(ancestor))
    }

    pub fn is_path_read_only(&self, path: &RelPath) -> bool {
        self.read_only_files.is_match(path)
    }

    pub fn is_std_path_read_only(&self, path: &Path) -> bool {
        self.read_only_files.is_match_std_path(path)
    }
}

pub fn is_default_excluded_component(name: &str) -> bool {
    matches!(
        name,
        ".git"
            | "node_modules"
            | "target"
            | "dist"
            | "build"
            | ".next"
            | ".cache"
            | "DerivedData"
            | "Library"
            | "coverage"
            | "tmp"
            | "logs"
    )
}

impl Settings for WorktreeSettings {
    fn from_settings(content: &settings::SettingsContent) -> Self {
        let worktree = content.project.worktree.clone();
        let file_scan_exclusions = worktree.file_scan_exclusions.unwrap().0;
        let file_scan_inclusions = worktree.file_scan_inclusions.unwrap();
        let private_files = worktree.private_files.unwrap().0;
        let hidden_files = worktree.hidden_files.unwrap();
        let read_only_files = worktree.read_only_files.unwrap_or_default();
        let scan_symlinks = worktree.scan_symlinks.unwrap();
        let parsed_file_scan_inclusions: Vec<String> = file_scan_inclusions
            .iter()
            .flat_map(|glob| {
                Path::new(glob)
                    .ancestors()
                    .skip(1)
                    .map(|a| a.to_string_lossy().into())
            })
            .filter(|p: &String| !p.is_empty())
            .collect();

        Self {
            prevent_sharing_in_public_channels: worktree.prevent_sharing_in_public_channels,
            file_scan_exclusions: path_matchers(file_scan_exclusions, "file_scan_exclusions")
                .log_err()
                .unwrap_or_default(),
            parent_dir_scan_inclusions: path_matchers(
                parsed_file_scan_inclusions,
                "file_scan_inclusions",
            )
            .unwrap(),
            file_scan_inclusions: path_matchers(file_scan_inclusions, "file_scan_inclusions")
                .unwrap(),
            private_files: path_matchers(private_files, "private_files")
                .log_err()
                .unwrap_or_default(),
            hidden_files: path_matchers(hidden_files, "hidden_files")
                .log_err()
                .unwrap_or_default(),
            read_only_files: path_matchers(read_only_files, "read_only_files")
                .log_err()
                .unwrap_or_default(),
            scan_symlinks,
            file_scan_depth: worktree.file_scan_depth.filter(|depth| *depth > 0),
        }
    }
}

fn path_matchers(mut values: Vec<String>, context: &'static str) -> anyhow::Result<PathMatcher> {
    values.sort();
    PathMatcher::new(values, PathStyle::local())
        .with_context(|| format!("Failed to parse globs from {}", context))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_file_scan_exclusions() {
        let settings = WorktreeSettings {
            prevent_sharing_in_public_channels: false,
            file_scan_exclusions: PathMatcher::default(),
            file_scan_inclusions: PathMatcher::default(),
            parent_dir_scan_inclusions: PathMatcher::default(),
            scan_symlinks: settings::ScanSymlinksSetting::Expanded,
            file_scan_depth: Some(5),
            private_files: PathMatcher::default(),
            hidden_files: PathMatcher::default(),
            read_only_files: PathMatcher::default(),
        };

        for name in &[
            ".git",
            "node_modules",
            "target",
            "dist",
            "build",
            ".next",
            ".cache",
            "DerivedData",
            "Library",
            "coverage",
            "tmp",
            "logs",
        ] {
            let path_str = format!("some/parent/{}", name);
            let path = RelPath::from_unix_str(&path_str).unwrap();
            assert!(
                settings.is_path_excluded(&path),
                "Expected {} to be excluded by default",
                name
            );
            let child_str = format!("some/parent/{}/deep/file.txt", name);
            let child = RelPath::from_unix_str(&child_str).unwrap();
            assert!(
                settings.is_path_excluded(&child),
                "Expected child in {} to be excluded by default",
                name
            );
        }

        let normal_path = RelPath::from_unix_str("src/main.rs").unwrap();
        assert!(!settings.is_path_excluded(&normal_path));
    }
}
