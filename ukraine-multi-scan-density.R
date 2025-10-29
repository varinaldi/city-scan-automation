source("R/setup.R")

pop_paths <- tibble(path = 
  list.files("mnt", recursive = T, full.names = T) %>%
    str_subset("ukraine") %>%
    str_subset("spatial.*population.tif$"),
  city = str_extract(path, "(?<=ukraine-).[a-z]*"))

pop_df <- pop_paths %>%
  apply(1, \(x) {
    df <- as_tibble(rast(x[["path"]])) %>%
      rename(pop = 1) %>%
      mutate(city = x[["city"]]) %>%
      filter(!is.na(pop))
  }) %>%
  bind_rows()

pop_df %>%
  mutate(city = str_to_title(city)) %>%
  ggplot(aes(x = pop)) +
  geom_histogram(bins = 100) +
  facet_grid(rows = vars(city)) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

density_plot <- pop_df %>%
  mutate(
    city = str_to_title(city),
    city = factor(city, levels = c(sort(setdiff(city, "Bucha")), "Bucha")),
    group = city == "Bucha") %>%
  ggplot(aes(x = pop, y = forcats::fct_rev(city), fill = group)) +
  geom_density(quantiles = 1:3/4, quantile_lines = TRUE, alpha = 0.6, scale = 0.9) + #, rel_min_height = 0.01) +
  scale_y_discrete(expand = expansion(0.05)) +
  labs(x = "Population density (people/hectare)") +
  theme_minimal() +
  theme(
    axis.title.y = element_blank(),
    legend.position = "none",
    # axis.line = element_line(linewidth = .5, color = "black"),
    panel.grid.major = element_line(linewidth = .125, color = "dark gray"),
    panel.grid.minor = element_line(linewidth = .125, linetype = 2, color = "dark gray"))

librarian::shelf(ggridges)


ggplot(iris, aes(x=Sepal.Length, y=Species, fill = factor(stat(quantile)))) +
  stat_density_ridges(
    geom = "density_ridges_gradient", calc_ecdf = TRUE,
    quantiles = 5, quantile_lines = FALSE
  ) +
  scale_fill_manual(
    name = "Density Percentile",
    values = c('#ECEB72', '#D4BE62', '#BD9252', '#A56542', '#8E3933'),
    labels = c("0-20th", "20-40th", "40-60th", "60-80th", "80-100th")
  ) +
  theme(legend.position = "bottom")

# density_plot <- 
pop_df %>%
  # group_by(city) %>%
  mutate(
    city = str_to_title(city),
    city = factor(city, levels = c(sort(setdiff(city, "Bucha")), "Bucha")),
    group = city == "Bucha",
    # n = n()
    ) %>%
  ungroup() %>%
  ggplot(aes(x = pop, y = forcats::fct_rev(city), fill = factor(stat(quantile)))) +
  stat_density_ridges(
    geom = "density_ridges_gradient", calc_ecdf = TRUE,
    # aes(height = n),
    quantiles = 1:4/5, quantile_lines = FALSE, 
    alpha = 0.6, scale = 0.9) + #, rel_min_height = 0.01) +
  scale_y_discrete(expand = expansion(0.05)) +
  scale_fill_manual(
    name = "Percentile",
    values = c('#ECEB72', '#D4BE62', '#BD9252', '#A56542', '#8E3933'),
    labels = c("0-20th", "20-40th", "40-60th", "60-80th", "80-100th")
  ) +
  labs(x = "Population density (people/hectare)") +
  theme_minimal() +
  theme(
    axis.title.y = element_blank(),
    legend.position = "bottom",
    # axis.line = element_line(linewidth = .5, color = "black"),
    panel.grid.major = element_line(linewidth = .125, color = "dark gray"),
    panel.grid.minor = element_line(linewidth = .125, linetype = 2, color = "dark gray"))

pop_totals <- tibble(
  city =       c("Bucha", "Makariv", "Mykolaiv", "Izyum", "Zaporizhzhia"),
  Pop = c(37321,        9390,     523955,   44979,        822336)
)

density_plot <- 
pop_df %>%
  # group_by(city) %>%
  mutate(
    city = str_to_title(city),
    # city = factor(city, levels = c(sort(setdiff(city, "Bucha")), "Bucha")),
    # group = city == "Bucha",
    # n = n()
    ) %>%
  ungroup() %>%
  ggplot(aes(x = pop, y = forcats::fct_rev(city), fill = factor(stat(quantile)))) +
  stat_density_ridges(
    geom = "density_ridges_gradient", calc_ecdf = TRUE,
    # aes(height = n),
    quantiles = 1:4/5, quantile_lines = FALSE, 
    alpha = 0.6, scale = 0.9) + #, rel_min_height = 0.01) +
  scale_x_continuous(breaks = seq(0, 80, 20), minor_breaks = seq(0, 80, 5), limits = c(-5, 80)) +
  # expand_limits(x = -10) +
  scale_y_discrete(expand = expansion(0.05)) +
  scale_fill_manual(
    name = "Percentile",
    values = c('#ECEB72', '#D4BE62', '#BD9252', '#A56542', '#8E3933'),
    labels = c("0-20th", "20-40th", "40-60th", "60-80th", "80-100th")
  ) +
  labs(x = "Population density (people/hectare)") +
  theme_minimal() +
  theme(
    axis.title.y = element_blank(),
    # legend.position = "bottom",
    # axis.line = element_line(linewidth = .5, color = "black"),
    panel.grid.major = element_line(linewidth = .125, color = "dark gray"),
    panel.grid.minor = element_line(linewidth = .125, linetype = 2, color = "dark gray")) +
  geom_point(data = pop_totals, aes(size = Pop, fill = NA), x = -5, fill = NA, shape = 1) +
  scale_size_area(
    name = "Total Population",
    breaks = range(pop_totals$Pop),
    labels = scales::label_comma()
    )

ggsave("plots/density-scatter.png", plot = density_plot, device = "png",
       width = 8, height = 5, units = "in", dpi = "print")

pop_df %>%
  mutate(
    city = str_to_title(city),
    city = factor(city, levels = c(sort(setdiff(city, "Bucha")), "Bucha")),
    group = city == "Bucha") %>%
  ggplot(aes(x = pop, y = forcats::fct_rev(city), fill = group)) +
  geom_density_ridges(stat = "binline", quantiles = 1:3/4, quantile_lines = TRUE, alpha = 0.6, scale = 0.9, rel_min_height = 0.001) +
  scale_y_discrete(expand = c(0, 0)) +
  labs(x = "Population density (people/hectare)") +
  theme_minimal() +
  theme(axis.title.y = element_blank(),
    # axis.line = element_line(linewidth = .5, color = "black"),
    panel.grid.major = element_line(linewidth = .125, color = "dark gray"),
    panel.grid.minor = element_line(linewidth = .125, linetype = 2, color = "dark gray"))


pop_df %>%
  mutate(city = str_to_title(city)) %>%
  ggplot(aes(x = pop)) +
  geom_density() +
  facet_grid(rows = vars(city))

pop_df %>%
  mutate(city = str_to_title(city)) %>%
  ggplot() +
  geom_boxplot(aes(x = city, y = pop)) +
  labs(y = "Population density (people/hectare)") +
  theme_minimal() +
  theme(axis.title.x = element_blank())

pop_df %>%
  mutate(city = str_to_title(city)) %>%
  ggplot() +
  geom_violin(aes(x = city, y = pop), draw_quantiles = 1:3/4) +
  labs(y = "Population density (people/hectare)") +
  theme_minimal() +
  theme(axis.title.x = element_blank())

pop_df %>%
  mutate(
    city = str_to_title(city),
    city = factor(city, levels = c("Bucha", sort(setdiff(city, "Bucha"))))) %>%
  ggplot() +
  geom_violin(aes(y = forcats::fct_rev(city), x = pop), draw_quantiles = 1:3/4, scale = "count") +
  labs(x = "Population density (people/hectare)") +
  theme_minimal() +
  theme(axis.title.y = element_blank(),
  axis.line = element_line(linewidth = .5, color = "black"),
    panel.grid.major = element_line(linewidth = .125, color = "dark gray"),
    panel.grid.minor = element_line(linewidth = .125, linetype = 2, color = "dark gray"))

stat_density_ridges
