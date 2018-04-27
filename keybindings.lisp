;; -*- mode: Lisp; eval: (stumpwm-mode 1); -*-

(in-package :stumpwm)

;; clear prior keys
(undefine-key *root-map* (kbd "k"))
(undefine-key *root-map* (kbd "C-k"))
(define-key *root-map* (kbd "C-k") NIL)

;; rofi
(define-key *root-map* (kbd "d") "exec rofi -show 'run'")

;; (define-key *root-map* (kbd "d") "exec firefox")
(define-key *root-map* (kbd "c") "exec kitty")
(define-key *root-map* (kbd "C-c") "exec kitty")
(define-key *root-map* (kbd "e") "exec kitty nvim")
(define-key *root-map* (kbd "C-e") "exec kitty nvim")
;; (define-key *root-map* (kbd "C-M-d") "exec systemctl poweroff")
;;TODO rebind redisplay, help-map, info
(define-key *root-map* (kbd "l") "move-focus right")
(define-key *root-map* (kbd "h") "move-focus left")
(define-key *root-map* (kbd "j") "move-focus down")
(define-key *root-map* (kbd "k") "move-focus up")
(define-key *root-map* (kbd "C-k") "move-focus up")

(define-key *root-map* (kbd "C-t") "meta C-t")

(defvar *toggle-map* (make-sparse-keymap))
(define-key *root-map* (kbd "t") '*toggle-map*)
(define-key *toggle-map* (kbd "g") "toggle-gaps")
(define-key *toggle-map* (kbd "m") "mode-line")

; rebind kill/delete
(define-key *root-map* (kbd "K") "delete")
(define-key *root-map* (kbd "C-K") "kill")

