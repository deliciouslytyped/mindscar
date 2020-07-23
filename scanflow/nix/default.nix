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
      i3
#      qtile
      (qtile.overridePythonAttrs (old: {
        src = ;#TODO
        patches = [];
        pythonPath = old.pythonPath ++ [ python37Packages.setuptools_scm ];

        postPatch = ''
          substituteInPlace libqtile/core/manager.py --subst-var-by out $out
          substituteInPlace libqtile/pangocffi.py --subst-var-by glib ${glib.out}
          substituteInPlace libqtile/pangocffi.py --subst-var-by pango ${pango.out}
          substituteInPlace libqtile/backend/x11/xcursors.py --subst-var-by xcb-cursor ${xorg.xcbutilcursor.out}
          '';


#        src = pkgs.fetchFromGitHub { owner = "qtile"; repo = "qtile"; rev = "v0.16.0"; sha256 = "1klv1k9847nyx71sfrhqyl1k51k2w8phqnp2bns4dvbqii7q125l"; };
#        patches = [ ./0001.patch ./0002.patch ./0003.patch ];
        }))

      gitAndTools.git-annex gitAndTools.gitFull
      ];
    };
  } 
