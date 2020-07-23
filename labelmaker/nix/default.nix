let
  sources = import ./sources.nix;
in
{ pkgs ? (import sources.nixpkgs {}) }: {
  bootstrap-shell = pkgs.mkShell {
    buildInputs = with pkgs; [ poetry niv ]; # niv is actually needed pre-bootstrap
    };
  shell = pkgs.mkShell {
    buildInputs = with pkgs; [ (poetry2nix.mkPoetryEnv { projectDir = ../src; }) sqlitebrowser dmtx-utils cups ]; # --pure makes cups necessary
    };
  } 
