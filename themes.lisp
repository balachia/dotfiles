;; -*- mode: Lisp; eval: (stumpwm-mode 1); -*-
(in-package :stumpwm)
(load-module "swm-gaps")
(load-module "globalwindows")

;; According to lepisma:
;; Inner gaps run along all the 4 borders of a frame
(setf swm-gaps:*inner-gaps-size* 12)

;; Outer gaps add more padding to the outermost borders
;; (touching the screen border)
(setf swm-gaps:*outer-gaps-size* 18)
;; end qoute

;; Remove window borders:
(setf *normal-window-border* 10)
(setf *window-border* 10)
;(setf *window-border-style* :thin)

(setf *message-window-gravity* :center
      *input-window-gravity* :center
      *message-window-padding* 10)


;; Call toggle-gaps
;; (run-commands "toggle-gaps")
;; (setf *gaps-on* t)
;; (define-key *root-map* (kbd "1") "toggle-gaps")

;; (clear-window-placement-rules)

;; fonts??
(load-module "ttf-fonts")
(xft:cache-fonts)
(set-font (make-instance
	   'xft:font
	   :family "Inconsolata-g"
	   :subfamily "g"
	   :size 10
           :antialias t))
