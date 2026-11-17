-- Datos de prueba realistas: 20 categorías, 20.000 productos, 10.000 clientes,
-- 30.000 pedidos y ~90.000 líneas de pedido (> 150.000 registros en total).
TRUNCATE order_items, orders, customers, products, categories RESTART IDENTITY CASCADE;

-- 1. Categorías Reales
INSERT INTO categories (name) VALUES
('Smartphones y Telefonía'),
('Portátiles y Computación'),
('Audio y Auriculares'),
('Televisores y Video'),
('Cámaras y Fotografía'),
('Videojuegos y Consolas'),
('Componentes de PC'),
('Hogar Inteligente'),
('Electrodomésticos'),
('Moda y Calzado'),
('Deportes y Fitness'),
('Relojes y Smartwatches'),
('Muebles y Decoración'),
('Cuidado Personal'),
('Juguetes y Hobbies'),
('Instrumentos Musicales'),
('Oficina y Papelería'),
('Herramientas y Bricolaje'),
('Accesorios de Viaje'),
('Libros y E-readers');

-- 2. Productos con nombres y descripciones realistas
INSERT INTO products (sku, name, description, category_id, price, stock)
WITH data AS (
  SELECT
    ARRAY[
      'Apple', 'Samsung', 'Sony', 'LG', 'Xiaomi', 'Asus', 'Dell', 'Lenovo',
      'HP', 'Bose', 'Logitech', 'Nike', 'Adidas', 'Canon', 'Philips', 'Razer',
      'Corsair', 'Nintendo', 'Microsoft', 'Anker'
    ] AS brands,
    ARRAY[
      'iPhone 15 Pro Max', 'Galaxy S24 Ultra Titanium', 'Pixel 8 Pro OLED', 'MacBook Air M3 15"', 'ThinkPad X1 Carbon Ultrabook',
      'Sony WH-1000XM5 Hi-Res', 'AirPods Pro 2 MagSafe', 'Smart TV OLED 55" 4K', 'PlayStation 5 Slim 1TB', 'Nintendo Switch OLED Neon',
      'GeForce RTX 4080 Gaming', 'Ryzen 7 7800X3D Box', 'Silla Ergonómica Transpirable', 'Zapatillas Running Pro Boost', 'Chaqueta Impermeable Polar',
      'Cafetera Espresso Italiana Pro', 'Freidora de Aire Dual Zone', 'Apple Watch Series 9 GPS', 'Drone 4K con Estabilizador', 'Kindle Paperwhite 16GB'
    ] AS models,
    ARRAY['Negro espacial', 'Plata titanio', 'Blanco alpino', 'Azul medianoche', 'Grafito mate', 'Verde bosque', 'Rojo carmesí', 'Oro champán'] AS colors,
    ARRAY['128GB', '256GB', '512GB', '1TB', 'Edición Especial', 'Pro Version', 'Plus Kit'] AS specs
)
SELECT
  'SKU-' || lpad(g::text, 6, '0') AS sku,
  (brands)[1 + (g % 20)] || ' ' || (models)[1 + (g % 20)] || ' - ' || (colors)[1 + (g % 8)] || ' (' || (specs)[1 + (g % 7)] || ')' AS name,
  'Producto original de alta gama ' || (brands)[1 + (g % 20)] || 
  '. Diseño ergonómico en acabado ' || (colors)[1 + (g % 8)] || 
  ', especificación ' || (specs)[1 + (g % 7)] || 
  '. Máximo rendimiento, garantía oficial directa de 12 meses y envío inmediato asegurado.' AS description,
  1 + (g % 20) AS category_id,
  round((29.99 + ((g * 43) % 1650) + random() * 49)::numeric, 2) AS price,
  (15 + (g % 180))::int AS stock
FROM generate_series(1, 20000) AS g, data;

-- 3. Clientes con nombres realistas
INSERT INTO customers (name, email, city)
WITH nombres AS (
  SELECT
    ARRAY['Carlos', 'María', 'Alejandro', 'Valentina', 'Juan Pablo', 'Camila', 'Andrés', 'Sofía', 'Daniel', 'Lucía', 'Mateo', 'Isabella', 'Diego', 'Mariana', 'Santiago', 'Gabriela', 'Nicolás', 'Paula', 'Felipe', 'Elena'] AS first_names,
    ARRAY['González', 'Rodríguez', 'López', 'Martínez', 'Gómez', 'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Díaz', 'Vargas', 'Morales', 'Castillo', 'Castro', 'Ortiz', 'Silva', 'Rojas', 'Reyes', 'García', 'Mendoza'] AS last_names
)
SELECT
  (first_names)[1 + (g % 20)] || ' ' || (last_names)[1 + ((g / 20) % 20)] AS name,
  lower((first_names)[1 + (g % 20)]) || '.' || lower((last_names)[1 + ((g / 20) % 20)]) || g || '@correo.com' AS email,
  (ARRAY['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Bucaramanga', 'Cartagena', 'Pereira', 'Manizales', 'Santa Marta', 'Cúcuta'])[1 + (g % 10)] AS city
FROM generate_series(1, 10000) AS g, nombres;

-- 4. Pedidos
INSERT INTO orders (customer_id, status, total, created_at)
SELECT 1 + ((g * 7919) % 10000),
       (ARRAY['PENDING', 'PAID', 'SHIPPED', 'DELIVERED'])[1 + (g % 4)],
       0,
       now() - make_interval(days => g % 365)
FROM generate_series(1, 30000) AS g;

-- 5. Líneas de Pedido
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, 1 + ((o.id + k) % 5), p.price
FROM orders o
CROSS JOIN generate_series(1, 3) AS k
JOIN products p ON p.id = 1 + ((o.id * 31 + k * 7919) % 20000);

-- Actualizar totales de pedidos
UPDATE orders
SET total = t.total
FROM (SELECT order_id, SUM(quantity * unit_price) AS total FROM order_items GROUP BY order_id) AS t
WHERE orders.id = t.order_id;

ANALYZE;
