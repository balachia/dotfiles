(setq package-archives '(("melpa" . "http://melpa.milkbox.net/packages/")
                         ("org" . "http://orgmode.org/elpa/")
                         ("gnu" . "http://elpa.gnu.org/packages/")))

(require 'package)
(package-initialize)



(require 'evil)
(evil-mode 1)

;; Enable evil-leader
(require 'evil-leader)
(global-evil-leader-mode)
(evil-leader/set-leader ",")

;; Enable transient mark mode
(transient-mark-mode 1)

;; enable parens mode
(show-paren-mode)

;; line numbers
(add-hook 'prog-mode-hook 'linum-mode)
(setq linum-format "%d ")

;;;;Org mode configuration
;; Enable Org mode
(require 'org)
;; Make Org mode work with files ending in .org
;; (add-to-list 'auto-mode-alist '("\\.org$" . org-mode))
;; The above is the default in recent emacsen

;; git
(require 'evil-magit)
(require 'evil-ediff)
(evil-leader/set-key
 "gs" 'magit-status)
;; (define-key evil-normal-state-map ",gs" 'magit-status)

;; nerd-commenter
(evil-leader/set-key
 "cl" 'evilnc-comment-or-uncomment-lines)

;; surround
(require 'evil-surround)
(global-evil-surround-mode 1)

;; helm
(require 'helm)
(require 'helm-config)
(helm-mode 1)
(global-set-key (kbd "C-c h") 'helm-command-prefix)
(global-unset-key (kbd "C-x c"))

(evil-leader/set-key
  ";" 'switch-to-buffer)

;; ess
(defun my-ess-start-R ()
  (interactive)
  (if (not (member "*R*" (mapcar (function buffer-name) (buffer-list))))
      (progn
	(delete-other-windows)
	(setq w1 (selected-window))
	(setq w1name (buffer-name))
	(setq w2 (split-window w1 nil t))
	(R)
	(set-window-buffer w2 "*R*")
	(set-window-buffer w1 w1name))))

(setq ess-ask-for-ess-directory nil)
;(setq inferior-ess-own-frame t)
;(setq inferior-ess-same-window nil)

;; basically, redo nvim-r bindings
(define-key evil-normal-state-map ",rf" 'my-ess-start-R)
(define-key evil-normal-state-map ",l" 'ess-eval-line)
(define-key evil-normal-state-map ",d" 'ess-eval-line-and-step)
(define-key evil-normal-state-map ",pa" 'ess-eval-paragraph-and-step)
(define-key evil-normal-state-map ",aa" 'ess-eval-buffer)

;; themes
(defun theme-light () (interactive)
       (load-theme 'material-light t))
(defun theme-dark () (interactive)
       (load-theme 'molokai t))

(defun toggle-theme ()
  (interactive)
  (let* ((ring '(theme-dark theme-light))
         (current (if (get 'theme-toggle 'state) (get 'theme-toggle 'state) -1))
         (next-idx (% (+ current 1) (length ring)))
         (next (nth next-idx ring))
         )
  (put 'theme-toggle 'state next-idx)
  (funcall next)))

(if (file-exists-p (expand-file-name "~/.theme"))
    (with-temp-buffer (insert-file-contents (expand-file-name "~/.theme"))
		      (if (string-equal (buffer-string) "light")
			  (theme-light)
			  (theme-dark)))
    (toggle-theme))

;; import vim keybinds
(define-key evil-normal-state-map ",tot" 'toggle-theme)
