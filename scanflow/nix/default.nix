let
  sources = import ./sources.nix;

  xnview-pack = builtins.fetchurl {
    url = "https://download.xnview.com/XnView_MP.glibc2.17-x86_64.AppImage";
    sha256 = "038k0xz61aa9izci8mfm7xvy9k1sammgpbvljcdb4z2d72535jrn";
    };
  xnview = {writeShellScriptBin, appimage-run}: writeShellScriptBin "xnview" ''
    ${appimage-run}/bin/appimage-run ${xnview-pack} $@
    '';

  py_upd_readline = pkgs: pkgs.python3.override (a: { readline = pkgs.readline80; }); # nixpkgs defaults to readline6 and i want some new functions

in
{ pkgs ? (import sources.nixpkgs {}) }: {
  bootstrap-shell = pkgs.mkShell {
    buildInputs = with pkgs; [ poetry niv ]; # niv is actually needed pre-bootstrap
    };
  shell = pkgs.mkShell {
    buildInputs = with pkgs; [
      (poetry2nix.mkPoetryEnv { projectDir = ../src;
         #python = py_upd_readline pkgs;
         })
      feh #(pkgs.callPackage xnview {}) viewnior feh gnome3.eog digikam
      sane-backends # for scanimage
      sqlitebrowser
      xorg.xorgserver #Xephyr
      konsole
      i3 (pkgs.callPackage ( /. + (pkgs.lib.fileContents ./qtilepath)) {})
      gitAndTools.git-annex gitAndTools.gitFull
      ];
    };
  } 
